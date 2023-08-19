 #!/bin/sh

echo ""
echo "Loading azd .env file from current environment"
echo ""

while IFS='=' read -r key value; do
    value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
    export "$key=$value"
done <<EOF
$(azd env get-values)
EOF

echo 'Creating python virtual environment "scripts/scripts_env"'
python3 -m venv scripts/scripts_env

echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/scripts_env/bin/python -m pip install -r scripts/requirements.txt

echo 'Running "prepdata.py"'
./scripts/scripts_env/bin/python ./scripts/prepdata.py