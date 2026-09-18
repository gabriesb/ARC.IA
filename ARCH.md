# Arquitetura — ARC.IA

Este documento detalha a arquitetura do **ARC.IA**: componentes de infraestrutura, fluxo de deploy (CI/CD), fluxo de geração de diagramas de arquitetura (via GitHub) e fluxo de recomendações de boas práticas (via AWS Knowledge MCP Server).

## Visão Geral (componentes)

```mermaid
flowchart TB
    subgraph GH["GitHub"]
        Repo["Repositório deste projeto\n(ARC.IA)"]
        Actions["GitHub Actions\n(build-push.yml)"]
        TargetRepo["Repositório(s) analisado(s)\npelo usuário (Terraform real)"]
    end

    subgraph AWS["AWS Account"]
        subgraph Bootstrap["infra_aws/ (bootstrap)"]
            OIDC["IAM OIDC Provider\ntoken.actions.githubusercontent.com"]
            Role["IAM Role\ngithub-actions-ecr"]
            ECR["Amazon ECR\nagent_ecr"]
            S3State["S3 Bucket\nagent-runtime-state\n(Terraform state)"]
            S3Diagrams["S3 Bucket\nagent-diagrams-*\n(diagramas .drawio)"]
            GitHubSecret["Secrets Manager\nagentcore-easy-deploy/github-token"]
        end

        subgraph Runtime["infra/ (runtime)"]
            RuntimeRole["IAM Role\nbedrock-agent-runtime-role-*"]
            AgentRuntime["AgentCore Runtime\nARC.IA (awscc_bedrockagentcore_runtime)"]
        end

        Bedrock["Amazon Bedrock\nNova Pro (apac.amazon.nova-pro-v1:0)"]
        CloudWatch["CloudWatch Logs"]
    end

    AWSDocs["AWS Knowledge MCP Server\n(knowledge-mcp.global.api.aws)\nsearch_documentation / read_documentation"]

    Client["Cliente / Invocador\n(payload JSON: prompt, owner/repo, terraform_code)"]

    Repo -->|PR devops_agent/arkia -> main\naprovado + merge (paths: src/**)| Actions
    Repo -.->|workflow_dispatch\naction=destroy| Actions
    Actions -->|assume role via OIDC| OIDC
    OIDC --> Role
    Actions -->|docker build + push\n(linux/arm64)| ECR
    Actions -->|terraform apply/destroy\n(infra/)| AgentRuntime
    AgentRuntime -->|pull image| ECR
    AgentRuntime -->|assume| RuntimeRole
    RuntimeRole -->|bedrock:InvokeModel| Bedrock
    RuntimeRole -->|logs:PutLogEvents| CloudWatch
    RuntimeRole -->|secretsmanager:GetSecretValue| GitHubSecret
    RuntimeRole -->|s3:PutObject/GetObject| S3Diagrams
    Role -->|s3:GetObject/PutObject| S3State

    Client -->|HTTPS invoke| AgentRuntime
    AgentRuntime -->|GitHub REST API\n(git trees + contents, .tf files)| TargetRepo
    AgentRuntime -->|HTTPS MCP\n(streamable HTTP, sem auth)| AWSDocs
    AgentRuntime -->|resposta JSON: result, diagram, recommendations| Client
```

## Fluxo de Deploy (CI/CD)

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Desenvolvedor
    participant GH as GitHub Repo
    participant GHA as GitHub Actions
    participant IAM as AWS IAM (OIDC)
    participant ECR as Amazon ECR
    participant TF as Terraform (infra/)
    participant Runtime as AgentCore Runtime

    Dev->>GH: PR devops_agent/arkia -> main (aprovado por reviewer)
    GH->>GH: merge do PR na main
    GH->>GHA: dispara build-push.yml (pull_request closed, merged=true)
    GHA->>IAM: AssumeRoleWithWebIdentity (OIDC token)
    IAM-->>GHA: credenciais temporárias (STS)
    GHA->>ECR: login + docker build (linux/arm64)
    GHA->>ECR: docker push (tag=merge-commit-sha e latest)
    GHA->>TF: terraform init + apply -var image_tag=merge-commit-sha
    TF->>Runtime: atualiza agent_runtime_artifact.container_uri
    Runtime->>ECR: pull da nova imagem
    Runtime-->>GHA: apply concluído
```

O workflow também expõe um disparo manual (`workflow_dispatch`) com dois modos:

- `action=apply`: repete o fluxo acima (build + push + terraform apply) sem depender de um PR.
- `action=destroy`: pula build/push e executa apenas `terraform destroy` em `infra/`, protegido pelo Environment `destroy-approval` (aprovação manual obrigatória).

## Fluxo de Geração de Diagrama (via GitHub)

Esta é a capacidade central do ARC.IA: **o diagrama nunca é desenhado pelo LLM**. Um caminho rápido determinístico identifica o repositório (payload explícito ou regex no prompt) e vai direto ao pipeline de parsing — o modelo só entra para orquestrar chamadas de ferramenta quando não há repositório/Terraform identificável.

```mermaid
sequenceDiagram
    autonumber
    participant Cliente
    participant Runtime as AgentCore Runtime
    participant App as agent.py (invoke)
    participant GH as github_client.py
    participant Parser as terraform_parser.py
    participant Builder as drawio_builder.py
    participant S3 as S3 (agent-diagrams-*)

    Cliente->>Runtime: POST /invoke {"owner", "repo_name", "ref"} ou {"prompt": "..."}
    Runtime->>App: invoke(payload)
    App->>App: identifica owner/repo (payload ou regex determinística no prompt)
    App->>GH: lista árvore do repo + baixa arquivos .tf/.tf.json
    GH-->>App: conteúdo dos arquivos Terraform
    App->>Parser: parse_terraform_files(files)
    Parser-->>App: resources[], edges[] (referências entre recursos)
    App->>Builder: build_drawio_xml(resources, edges)
    Builder->>Builder: layout em camadas por dependência + ícones AWS4 + legenda
    Builder-->>App: XML .drawio
    App->>S3: upload do .drawio (best-effort)
    S3-->>App: URL pré-assinada
    App-->>Runtime: {"result", "diagram": {xml, download_url}, "resources"}
    Runtime-->>Cliente: resposta JSON
```

## Fluxo de Boas Práticas (Well-Architected)

Quando o prompt do usuário indica intenção de avaliação (ex: "boas práticas", "recomendação", "é uma boa prática usar X?"), o ARC.IA aciona o LLM com acesso ao **AWS Knowledge MCP Server** — nunca responde com uma opinião não verificada.

```mermaid
sequenceDiagram
    autonumber
    participant Cliente
    participant App as agent.py (invoke)
    participant Agent as Strands Agent
    participant MCP as AWS Knowledge MCP Server
    participant Bedrock as Amazon Bedrock (Nova Pro)

    Cliente->>App: prompt com intenção de boas práticas\n(regex determinística detecta a intenção)
    App->>Agent: pede revisão dos tipos de recurso encontrados
    Agent->>MCP: search_documentation / read_documentation
    MCP-->>Agent: trechos da documentação oficial (com URL)
    Agent->>Bedrock: InvokeModel (system_prompt + docs + pergunta)
    Bedrock-->>Agent: recomendação fundamentada, citando a(s) URL(s)
    Agent-->>App: texto da recomendação
    App-->>Cliente: {"recommendations": "..."} (junto com o diagrama, se houver)
```

## Fluxo de Execução — Fallback Conversacional

Quando nenhum repositório/Terraform é identificado, o agente cai no modo conversacional — ainda assim, as mesmas ferramentas determinísticas (diagrama) e as ferramentas MCP (documentação) continuam disponíveis ao modelo.

```mermaid
sequenceDiagram
    autonumber
    participant Cliente
    participant Runtime as AgentCore Runtime
    participant App as BedrockAgentCoreApp (agent.py)
    participant Agent as Strands Agent
    participant Bedrock as Amazon Bedrock (Nova Pro)

    Cliente->>Runtime: POST /invoke {"prompt": "..."}
    Runtime->>App: invoke(payload)
    App->>App: nenhum owner/repo/terraform_code identificado
    App->>Agent: agent(user_prompt)
    Agent->>Bedrock: InvokeModel (system_prompt + prompt + tools disponíveis)
    Bedrock-->>Agent: resposta do modelo (pode incluir chamadas às tools de diagrama/docs)
    Agent-->>App: result.message
    App-->>Runtime: {"result": "..."}
    Runtime-->>Cliente: resposta JSON
```

## Camadas e Responsabilidades

| Camada | Diretório | Responsabilidade |
|---|---|---|
| Bootstrap | [infra_aws/](infra_aws) | Cria pré-requisitos que só existem uma vez: ECR, bucket de state, IAM Role + OIDC do GitHub Actions, bucket S3 de diagramas e o secret do GitHub token (o `infra/` apenas referencia esses recursos via `data` sources) |
| Runtime (IaC) | [infra/](infra) | Provisiona o `AgentCore Runtime` e a IAM Role que ele assume para chamar o Bedrock, ler o GitHub token e escrever diagramas no S3 |
| Aplicação | [src/](src) | `agent.py` (entrypoint + tools + MCP), `diagram_service.py` (orquestração), `terraform_parser.py` (parsing determinístico), `drawio_builder.py` (layout/render), `aws_icon_map.py` (ícones/categorias), `github_client.py` (API REST do GitHub), `Dockerfile` e dependências |
| CI/CD | [.github/workflows/](.github/workflows) | Builda a imagem, publica no ECR e aplica o Terraform do runtime quando um PR `devops_agent`/`arkia` → `main` é aprovado/mergeado; também permite `apply`/`destroy` manuais via `workflow_dispatch` |

## Rede e Segurança (estado atual)

- `network_configuration.network_mode = "PUBLIC"` no [infra/agentcore_runtime.tf](infra/agentcore_runtime.tf) — o runtime é acessível publicamente (sem VPC privada), e precisa de saída HTTPS pública para chamar a API do GitHub e o AWS Knowledge MCP Server.
- Autenticação da pipeline via **OIDC** (sem chaves de acesso estáticas no GitHub).
- O GitHub PAT usado para ler repositórios fica apenas no Secrets Manager (`GITHUB_TOKEN_SECRET_ARN`), nunca no código, no state do Terraform ou nos logs.
- O AWS Knowledge MCP Server é público e não exige autenticação — está sujeito a rate limiting por parte da AWS; uma falha de conexão é tolerada (`continue_on_error=True`) e apenas remove as ferramentas de documentação daquela chamada, sem quebrar a geração de diagrama.
- State do Terraform armazenado remotamente em S3 ([infra/versions.tf](infra/versions.tf)), sem lock (DynamoDB).

## Ordem de Provisionamento e Destruição

```mermaid
flowchart LR
    subgraph Criacao["Criação"]
        A["1. infra_aws\n(bootstrap)"] --> B["2. Pipeline GitHub Actions\n(build + push + infra apply)"]
    end
    subgraph Destruicao["Destruição"]
        C["1. infra\n(destroy runtime\nvia pipeline, action=destroy)"] --> D["2. infra_aws\n(destroy bootstrap,\nmanual)"]
    end
```

Para detalhes de deploy passo a passo, consulte o [README.MD](README.MD).
