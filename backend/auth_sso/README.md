# PlanMincit - Auth SSO (FastAPI)

## Run (dev)
1) Create venv + install deps
2) Generate RSA keys
3) Init DB seed
4) Run uvicorn

### Keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out keys/jwt_private.pem
openssl rsa -pubout -in keys/jwt_private.pem -out keys/jwt_public.pem

### Seed
python -m app.db.init_seed

### Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
