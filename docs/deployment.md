# Deployment

This guide describes a generic EC2-style deployment. Adapt paths, users, and
domains to your environment.

## Host Setup

```bash
cd /opt
git clone <repository-url> pain-narratives-app-public
cd pain-narratives-app-public

curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Copy private runtime files from your secret store:

- `config.yaml` or another YAML file referenced by `PAIN_NARRATIVES_CONFIG`
- Optional `.streamlit/config.toml`

Run migrations:

```bash
cd src/pain_narratives/db
uv run alembic upgrade head
cd ../../..
```

Create an admin user if this is a new database:

```bash
uv run python scripts/register_user.py
```

## Running the App

Development-style launch:

```bash
make app
```

Production deployments should use a process manager such as `systemd`.

## systemd Template

The repository includes `deploy/pain-narratives.service`. Copy it to the host
unit directory and fill in placeholders:

```bash
sudo cp deploy/pain-narratives.service /etc/systemd/system/pain-narratives.service
sudo $EDITOR /etc/systemd/system/pain-narratives.service
sudo systemctl daemon-reload
sudo systemctl enable --now pain-narratives
```

Use an environment file for host-specific settings:

```ini
EnvironmentFile=-/etc/pain-narratives.env
```

Example `/etc/pain-narratives.env`:

```text
PAIN_NARRATIVES_CONFIG=/etc/pain-narratives/config.yaml
```

## Bedrock Access

Bedrock-backed models use standard AWS credential resolution unless a profile or
bearer token is configured. Preferred order:

1. IAM role or instance profile.
2. Named AWS profile via `bedrock.aws_profile` or `--bedrock-profile`.
3. Bedrock bearer token in private config.

Validate before running a batch:

```bash
aws sts get-caller-identity
uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
uv run python scripts/dev/test_bedrock_smoke.py --model sonnet-4-5-thinking
```

### EC2 IAM Role (recommended for production)

Attach a role to the instance instead of storing long-lived IAM user keys in
`~/.aws/credentials`. The role needs only Bedrock data-plane access for the
foundation model + cross-region inference profile the app actually uses.

If your IAM user does not have `iam:CreateRole`, send the snippets below to
whoever administers your AWS account. After they attach the instance profile,
clear `bedrock.aws_profile` in `config.yaml`, restart the service, and confirm
`aws sts get-caller-identity` on the box returns the role ARN.

Trust policy (allow EC2 to assume the role):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions policy (scope to the Claude Sonnet 4.5 cross-region profile; add
other foundation-model ARNs as needed). Replace `<ACCOUNT_ID>`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "InvokeClaudeSonnet45CrossRegion",
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream"
    ],
    "Resource": [
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    ]
  }]
}
```

Admin commands (substitute `<ROLE_NAME>`, e.g. `pain-narratives-ec2-bedrock`,
and `<INSTANCE_ID>`):

```bash
aws iam create-role --role-name <ROLE_NAME> \
  --assume-role-policy-document file://ec2-trust.json
aws iam put-role-policy --role-name <ROLE_NAME> \
  --policy-name bedrock-claude-sonnet-4-5 \
  --policy-document file://bedrock-policy.json
aws iam create-instance-profile --instance-profile-name <ROLE_NAME>
aws iam add-role-to-instance-profile --instance-profile-name <ROLE_NAME> \
  --role-name <ROLE_NAME>
aws ec2 associate-iam-instance-profile --instance-id <INSTANCE_ID> \
  --iam-instance-profile Name=<ROLE_NAME>
```

Until the role is attached, the app falls through to whatever
`~/.aws/credentials` provides. Restrict that file to `chmod 600` and prefer a
non-MFA IAM user whose access keys are scoped to the same Bedrock actions.

## Smoke Test

After deployment:

```bash
systemctl status pain-narratives
journalctl -u pain-narratives -n 100 --no-pager
```

Then verify in the UI:

- Login works.
- Evaluation groups load.
- A narrative can be selected.
- Admin user management is available to admin users.

Run the local test suite on the host without live integrations:

```bash
uv run pytest
```

Run live integration checks only with explicit private config:

```bash
RUN_LIVE_DB_TESTS=1 PAIN_NARRATIVES_CONFIG=/secure/path/config.yaml uv run pytest -m live_db
```
