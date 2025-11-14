#!/bin/bash
# ============================================================================
# Database Migration Runner
# ============================================================================
# Purpose: Execute SQL migration scripts on all database files
# Usage:
#   ./scripts/run_migration.sh [migration_file]
#   ./scripts/run_migration.sh database/migrations/001_add_remarks_to_blood_events.sql
#   ./scripts/run_migration.sh --all  (run all pending migrations)
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_DBS=0
SUCCESS_COUNT=0
SKIP_COUNT=0
ERROR_COUNT=0

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to run migration on a single database
run_migration_on_db() {
    local db_file=$1
    local migration_file=$2
    local db_name=$(basename "$db_file")

    TOTAL_DBS=$((TOTAL_DBS + 1))

    # Check if database file exists
    if [ ! -f "$db_file" ]; then
        print_warning "$db_name: Database file not found, skipping"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        return
    fi

    # Check if migration file exists
    if [ ! -f "$migration_file" ]; then
        print_error "$db_name: Migration file not found: $migration_file"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        return
    fi

    # Execute migration using Python
    echo -n "  Migrating $db_name... "

    RESULT=$(python3 << EOF
import sqlite3
import sys

try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()

    # Read and execute migration SQL
    with open('$migration_file', 'r') as f:
        sql = f.read()
        # Remove comments and split by semicolon
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    for statement in statements:
        if statement:
            try:
                cursor.execute(statement)
            except sqlite3.OperationalError as e:
                if 'duplicate column' in str(e).lower():
                    print('SKIP')
                    sys.exit(0)
                else:
                    print(f'ERROR: {e}')
                    sys.exit(1)

    conn.commit()
    conn.close()
    print('SUCCESS')
    sys.exit(0)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
EOF
)

    if echo "$RESULT" | grep -q "SUCCESS"; then
        print_success "Success"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif echo "$RESULT" | grep -q "SKIP"; then
        print_warning "Column already exists (skipped)"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        print_error "Failed: $RESULT"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
}

# Function to verify migration
verify_migration() {
    local db_file=$1
    local column_name=$2
    local table_name=$3

    RESULT=$(python3 << EOF
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info($table_name)')
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    if '$column_name' in columns:
        print('FOUND')
    else:
        print('NOT_FOUND')
except Exception as e:
    print('ERROR')
EOF
)

    if echo "$RESULT" | grep -q "FOUND"; then
        return 0  # Column exists
    else
        return 1  # Column doesn't exist
    fi
}

# Main execution
main() {
    echo "======================================================================"
    echo "🗄️  Database Migration Runner"
    echo "======================================================================"
    echo ""

    # Parse arguments
    if [ $# -eq 0 ]; then
        print_error "Usage: $0 <migration_file> or $0 --all"
        echo ""
        echo "Examples:"
        echo "  $0 database/migrations/001_add_remarks_to_blood_events.sql"
        echo "  $0 --all"
        exit 1
    fi

    MIGRATION_FILE=$1

    if [ "$MIGRATION_FILE" = "--all" ]; then
        print_info "Running all migrations from database/migrations/"

        # Check if migrations directory exists
        if [ ! -d "database/migrations" ]; then
            print_error "Migrations directory not found: database/migrations/"
            exit 1
        fi

        # Get all migration files (sorted)
        MIGRATION_FILES=$(find database/migrations -name "*.sql" | sort)

        if [ -z "$MIGRATION_FILES" ]; then
            print_warning "No migration files found in database/migrations/"
            exit 0
        fi

        # Run each migration
        for mig_file in $MIGRATION_FILES; do
            echo ""
            print_info "Running migration: $(basename $mig_file)"
            echo ""

            # Find all database files
            for db in database/*_general.db medical_inventory.db; do
                if [ -f "$db" ]; then
                    run_migration_on_db "$db" "$mig_file"
                fi
            done
        done
    else
        # Single migration file
        if [ ! -f "$MIGRATION_FILE" ]; then
            print_error "Migration file not found: $MIGRATION_FILE"
            exit 1
        fi

        print_info "Running migration: $(basename $MIGRATION_FILE)"
        echo ""

        # Find all database files and run migration
        print_info "Searching for database files..."
        echo ""

        # Migrate main database
        if [ -f "medical_inventory.db" ]; then
            run_migration_on_db "medical_inventory.db" "$MIGRATION_FILE"
        fi

        # Migrate station databases
        for db in database/*_general.db; do
            if [ -f "$db" ]; then
                run_migration_on_db "$db" "$MIGRATION_FILE"
            fi
        done

        # Migrate test databases if they exist
        for db in database/test_*_general.db; do
            if [ -f "$db" ]; then
                run_migration_on_db "$db" "$MIGRATION_FILE"
            fi
        done
    fi

    # Print summary
    echo ""
    echo "======================================================================"
    echo "📊 Migration Summary"
    echo "======================================================================"
    echo "  Total databases: $TOTAL_DBS"
    echo -e "  ${GREEN}Successful: $SUCCESS_COUNT${NC}"
    echo -e "  ${YELLOW}Skipped: $SKIP_COUNT${NC}"
    echo -e "  ${RED}Failed: $ERROR_COUNT${NC}"
    echo "======================================================================"

    # Verification (for migration 001)
    if echo "$MIGRATION_FILE" | grep -q "001_add_remarks_to_blood_events"; then
        echo ""
        print_info "Verifying migration..."
        echo ""

        # Check main database
        if [ -f "medical_inventory.db" ]; then
            if verify_migration "medical_inventory.db" "remarks" "blood_events"; then
                print_success "medical_inventory.db: remarks column verified"
            else
                print_error "medical_inventory.db: remarks column not found"
            fi
        fi
    fi

    echo ""
    if [ $ERROR_COUNT -eq 0 ]; then
        print_success "Migration completed successfully!"
        exit 0
    else
        print_error "Migration completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"
