# Main justfile for dr-daily-report
# 
# This justfile uses a modular structure for better organization:
# - dev.just: Development commands (run server, tests, etc.)
# - deploy.just: Deployment commands (build, deploy, etc.)
# - utils.just: Utility commands (clean, format, etc.)
#
# Note: Recipes run from justfile-modules/ directory, so all paths
# use '../' to navigate to the project root.

import 'justfile-modules/dev.just'
import 'justfile-modules/deploy.just'
import 'justfile-modules/utils.just'

# Default recipe - show available commands
default:
    @just --list