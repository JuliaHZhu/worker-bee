#!/bin/bash
# Shared configuration for Worker-Bee shell scripts
# Usage: source "$(dirname "$0")/common.sh"

# Load PM node IP from environment or default to loopback
PM_IP="${BEE_PM_IP:-127.0.0.1}"
