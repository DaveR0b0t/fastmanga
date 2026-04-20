#!/bin/bash
# FastManga Installation Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}${1}${NC}"
}

print_success() {
    echo -e "${GREEN}${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}${1}${NC}"
}

print_error() {
    echo -e "${RED}${1}${NC}"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        print_success "$1 is installed"
        return 0
    else
        print_warning "$1 is not installed"
        return 1
    fi
}

echo ""
echo "FastManga Installation Script"
echo ""

print_info "Checking Python installation..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        print_success "Python $PYTHON_VERSION detected"
    else
        print_error "Python 3.10 or higher is required. Found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 is not installed"
    exit 1
fi

print_info "Checking pip installation..."
if ! command -v pip3 >/dev/null 2>&1; then
    print_warning "pip3 not found. Attempting to install..."
    python3 -m ensurepip --default-pip || {
        print_error "Failed to install pip"
        exit 1
    }
fi
print_success "pip is available"

echo ""
print_info "Installing FastManga..."
pip3 install -e . || {
    print_error "Failed to install FastManga"
    exit 1
}
print_success "FastManga installed successfully"

echo ""
print_info "Checking optional dependencies..."
check_command fzf || print_info "fzf improves the search workflow"

HAS_RENDERER=false
if check_command chafa; then
    HAS_RENDERER=true
elif check_command kitten; then
    HAS_RENDERER=true
    print_info "Detected kitty terminal"
else
    print_warning "No image renderer found"
    print_info "Install chafa or use a terminal with kitty icat"
fi

echo ""
print_info "Initializing configuration..."
fastmanga config init || {
    print_warning "Could not initialize config automatically"
    print_info "Run 'fastmanga config init' manually"
}

echo ""
print_success "Installation complete"
echo ""
echo "Quick Start"
echo "  fastmanga search \"One Piece\""
echo "  fastmanga read \"Naruto\" -c 1"
echo "  fastmanga download \"Berserk\" -c 1-10"
echo "  fastmanga library list"
echo "  fastmanga --help"
echo ""
echo "See README.md for more details"
