set -e # Stop by any error

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # path to root where the "start.sh" is located
cd "$DIR"/scripts # move to dir with generator

# Choosing the right interpreter
if command -v python3 &> /dev/null && [[ "$(command -v python3)" != *WindowsApps* ]]; then
    PYTHON=python3
elif command -v python &> /dev/null && [[ "$(command -v python)" != *WindowsApps* ]]; then
    PYTHON=python
else
    echo "Python don't find"
    exit 1
fi

$PYTHON gen_shared_env.py # Creating .env.shared

cd .. # Back to root

docker compose up --build # Build and start Docker Compose