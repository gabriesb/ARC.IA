# GeoPro AgentCore

Agente de Inteligência Artificial especializado em **Geografia**, executado nativamente no **AWS Bedrock AgentCore Runtime**, com infraestrutura provisionada via **Terraform (AWS Cloud Control – awscc)** e pipelines **CI/CD manuais**.

Este projeto demonstra uma arquitetura moderna de **GenAI + DevOps**, com foco em controle total do ambiente, reprodutibilidade, segurança e boas práticas de produção.

---

## Visão Geral

O **GeoPro AgentCore** é um agente de IA projetado para responder perguntas complexas de Geografia de forma **precisa, estruturada e didática**, respeitando limites claros de domínio e evitando respostas genéricas ou fora de escopo.

O runtime do agente é containerizado e executado diretamente no **AgentCore**, sem dependência de front-end, APIs externas ou serviços intermediários.

---

## Objetivos do Projeto

- Executar um agente de IA diretamente no **AWS Bedrock AgentCore**
- Utilizar **containers ARM64**, compatíveis com a infraestrutura do AgentCore
- Provisionar toda a infraestrutura com **Terraform (awscc provider)**
- Separar claramente:
  - build de imagem
  - provisionamento de infraestrutura
  - destruição do ambiente
- Garantir **execução manual** das pipelines, evitando custos e alterações acidentais

---

## Capacidades do Agente

### Geografia Física
- Tipos climáticos e fatores climáticos
- Relevo, formas de terreno e processos de formação
- Biomas e ecossistemas
- Oceanos, rios e ciclo hidrológico
- Tectônica de placas, terremotos e vulcanismo

### Geografia Humana
- Distribuição populacional e densidade demográfica
- Urbanização, megacidades e impactos urbanos
- Geopolítica e fronteiras internacionais
- Migração e dinâmica territorial

### Geografia Econômica
- Recursos naturais e sua distribuição
- Produção agrícola, industrial e extrativa
- Logística, infraestrutura e cadeias de suprimento
- Rotas comerciais históricas e atuais

### Geografia Ambiental
- Mudanças climáticas e seus impactos
- Sustentabilidade e desenvolvimento sustentável
- Conservação ambiental e serviços ecossistêmicos

### Cartografia
- Latitude e longitude
- Coordenadas geográficas
- Fusos horários e Linha Internacional de Data

---

## Arquitetura

GitHub Repository
│
├── Docker (ARM64)
│ └── Container do agente
│
├── Amazon ECR
│ └── Armazenamento das imagens
│
├── AWS Bedrock AgentCore
│ └── Execução do runtime de IA
│
└── Terraform (awscc)
└── Provisionamento da infraestrutura

yaml
Copiar código

---

## Estrutura do Repositório

.
├── agent.py # Lógica do agente de Geografia
├── Dockerfile # Runtime container (ARM64)
├── requirements.txt # Dependências Python
├── infra/
│ ├── main.tf # Recursos principais (ECR, IAM, AgentCore)
│ ├── variables.tf # Variáveis do Terraform
│ ├── outputs.tf # Outputs (ECR, Runtime)
│ ├── providers.tf # Providers AWS / awscc
│ └── versions.tf # Versões do Terraform
└── .github/
└── workflows/
├── agentcore-runtime.yml # Build & Push da imagem (manual)
├── terraform-setup.yml # Terraform Apply (manual)
└── terraform-destroy.yml # Terraform Destroy (manual + seguro)

yaml
Copiar código

---

## Pipelines CI/CD

Todas as pipelines são **manuais**, acionadas apenas via `workflow_dispatch`.

### Build & Push do Runtime
- Build da imagem Docker usando **Docker Buildx**
- Arquitetura: `linux/arm64`
- Push direto para o Amazon ECR

### Terraform Apply
- Inicializa e valida o Terraform
- Cria ou atualiza:
  - Repositório ECR
  - IAM Roles e Policies
  - AgentCore Runtime

### Terraform Destroy
- Execução manual com confirmação explícita
- Limpa imagens do ECR antes do destroy
- Remove toda a infraestrutura provisionada

---

## Requisitos

- Conta AWS com **Bedrock AgentCore habilitado**
- Docker com **Buildx**
- Terraform `>= 1.6`
- GitHub Actions
- Permissões AWS para:
  - ECR
  - IAM
  - Bedrock AgentCore
  - Cloud Control API

---

## Segurança e Boas Práticas

- Terraform state não é versionado
- `.terraform.lock.hcl` versionado para reprodutibilidade
- Secrets armazenados apenas no GitHub Actions
- Execução manual de pipelines para controle de custos
- Infraestrutura declarativa e idempotente
- Separação clara entre código, build e infraestrutura

---

## Exemplo de Uso

Payload de invocação do runtime:

```json
{
  "prompt": "Explique por que os desertos se concentram próximos aos 30 graus de latitude."
}
O agente retorna uma resposta estruturada, objetiva e específica do domínio geográfico.

Possíveis Evoluções
Exposição via AgentCore Gateway (API REST)

Suporte a múltiplos ambientes (dev / prod)

OIDC para CI/CD (remoção de chaves estáticas)

Ferramentas geográficas adicionais (clima, coordenadas, fusos)

Monitoramento e métricas avançadas

Autor
Projeto desenvolvido como portfólio técnico em DevOps e Generative AI, com foco em:

Infraestrutura como Código

Arquiteturas cloud-native

GenAI em produção

Pipelines CI/CD seguras e controladas