# Terraform — AWS infrastructure

Provisiona a infraestrutura de nuvem para rodar a plataforma em produção:

- **VPC** com subnets públicas/privadas em 3 AZs e NAT gateway
- **EKS** (control plane + managed node group com autoscaling)
- **RDS PostgreSQL** (criptografado, Multi-AZ em prod)
- **ElastiCache Redis** (replication group, criptografia at-rest/in-transit)

A separação de ambientes é feita via `environment` (e idealmente um workspace ou
diretório de backend por ambiente). Em `prod`, o código liga Multi-AZ, failover e
deletion protection automaticamente.

## Uso

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars

export TF_VAR_db_password="$(openssl rand -base64 24)"

terraform init
terraform plan
terraform apply

# Configurar o kubectl no cluster recém-criado
$(terraform output -raw configure_kubectl)
```

Depois, aplique os manifests (ou aponte o ArgoCD):

```bash
kubectl apply -k ../../deploy/k8s/overlays/prod
```

## Notas

- O state remoto (S3 + DynamoDB lock) está comentado em `versions.tf` — habilite antes
  de usar em equipe.
- A senha do banco **nunca** deve ser versionada; injete via `TF_VAR_db_password` ou um
  secret manager (AWS Secrets Manager / SSM). Os endpoints de RDS/Redis saem como outputs
  para alimentar o `Secret`/`ConfigMap` do cluster (idealmente via External Secrets Operator).
- Os módulos `terraform-aws-modules/{vpc,eks}` são versionados (`~>`) para builds reprodutíveis.
