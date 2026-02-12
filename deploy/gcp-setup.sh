#!/usr/bin/env bash
# GCP VM setup script for Arcuate Chief of Staff Agent
# Run this on a fresh GCP Compute Engine VM (Ubuntu 22.04 or Debian 12)
#
# Prerequisites:
#   1. Create a VM: gcloud compute instances create arcuate-agent \
#        --zone=us-central1-a --machine-type=e2-small \
#        --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud \
#        --boot-disk-size=20GB --tags=http-server
#   2. Open firewall: gcloud compute firewall-rules create allow-8000 \
#        --allow=tcp:8000 --target-tags=http-server
#   3. Reserve static IP: gcloud compute addresses create arcuate-ip --region=us-central1
#   4. Assign it: gcloud compute instances delete-access-config arcuate-agent --zone=us-central1-a \
#        && gcloud compute instances add-access-config arcuate-agent --zone=us-central1-a \
#        --address=$(gcloud compute addresses describe arcuate-ip --region=us-central1 --format='value(address)')
#   5. SSH in: gcloud compute ssh arcuate-agent --zone=us-central1-a
#   6. Run this script: bash deploy/gcp-setup.sh

set -euo pipefail

echo "=== Installing system dependencies ==="
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

echo "=== Cloning repo ==="
cd /opt
sudo git clone https://github.com/pangal-nsgy/arcuate_agents.git || true
cd /opt/arcuate_agents

echo "=== Setting up Python environment ==="
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install .

echo "=== Creating data directories ==="
sudo mkdir -p /opt/arcuate_agents/data

echo "=== Setting up systemd service ==="
sudo tee /etc/systemd/system/arcuate-agent.service > /dev/null <<'UNIT'
[Unit]
Description=Arcuate Chief of Staff Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/arcuate_agents
EnvironmentFile=/opt/arcuate_agents/.env
ExecStart=/opt/arcuate_agents/venv/bin/python -m uvicorn chief_of_staff.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable arcuate-agent
sudo systemctl start arcuate-agent

echo ""
echo "=== DONE ==="
echo "Agent is running on port 8000"
echo ""
echo "NEXT STEPS:"
echo "  1. Copy your .env file:        scp .env <vm-ip>:/opt/arcuate_agents/.env"
echo "  2. Copy your token.json:        scp token.json <vm-ip>:/opt/arcuate_agents/token.json"
echo "  3. Copy your credentials.json:  scp credentials.json <vm-ip>:/opt/arcuate_agents/credentials.json"
echo "  4. Restart:                      sudo systemctl restart arcuate-agent"
echo "  5. Set Twilio webhook to:        http://<vm-ip>:8000/webhooks/twilio/sms"
echo "  6. Check logs:                   sudo journalctl -u arcuate-agent -f"
