GeoPro AgentCore

Agente de Inteligência Artificial Especializado em Geografia com AWS Bedrock AgentCore

Visão Geral

GeoPro AgentCore é um agente de Inteligência Artificial especializado em Geografia, desenvolvido para rodar nativamente no AWS Bedrock AgentCore Runtime. O projeto combina Infraestrutura como Código (Terraform), runtimes containerizados de IA e pipelines CI/CD para oferecer uma solução escalável e pronta para produção.

O agente é projetado para fornecer respostas precisas, estruturadas e educacionais em múltiplos domínios da Geografia, seguindo rigorosos limites de comportamento e domínio.

Objetivos Principais

Implantar um agente de IA totalmente gerenciado pelo AWS Bedrock AgentCore

Garantir builds de container ARM64 (requisito do AgentCore)

Usar Terraform (AWS Cloud Control – awscc provider) para gerenciar a infraestrutura

Separar as pipelines de build das pipelines de infraestrutura

Seguir as melhores práticas DevOps em produção

Capacidades do Agente
Geografia Física

Tipos climáticos e fatores climáticos

Formações de relevo e seus processos de formação

Biomas e ecossistemas

Oceanos, rios e ciclos hidrológicos

Tectônica de placas, terremotos e vulcanismo

Geografia Humana

Distribuição da população, densidade e tendências demográficas

Urbanização, megacidades e o impacto do crescimento urbano

Geopolítica, fronteiras políticas e disputas territoriais

Fronteiras e seu impacto econômico e social

Geografia Econômica

Recursos naturais e sua distribuição

Produção agrícola e industrial

Logística, redes de transporte e cadeias de suprimento

Rotas comerciais históricas e contemporâneas

Geografia Ambiental

Mudanças climáticas: causas, consequências, mitigação e adaptação

Sustentabilidade e práticas de desenvolvimento sustentável

Serviços ecossistêmicos e conservação da biodiversidade

Fundamentos de Cartografia

Latitude, longitude e posicionamento geográfico

Fusos horários e a Linha Internacional de Data

Arquitetura do Projeto
Repositório GitHub
│
├── Docker (ARM64)
│   └── Container do Agent Runtime
│
├── AWS ECR
│   └── Armazena as imagens do runtime
│
├── AWS Bedrock AgentCore
│   └── Executa o agente de IA
│
└── Terraform (awscc provider)
    └── Gerencia toda a infraestrutura

Estrutura do Projeto
.
├── agent.py                    # Lógica do agente de Geografia
├── Dockerfile                  # Container compatível com ARM64
├── requirements.txt            # Dependências do runtime
├── infra/
│   ├── main.tf                 # AgentCore runtime & IAM
│   ├── providers.tf            # Provedores AWS (awscc)
│   ├── versions.tf             # Restrições de versão do Terraform
│   ├── variables.tf            # Variáveis de entrada
│   └── outputs.tf              # Outputs do runtime & ECR
└── .github/
    └── workflows/
        ├── agentcore-runtime.yml      # Build & push da imagem ARM64
        ├── terraform-setup.yml        # Aplicação do Terraform (ambiente)
        └── terraform-destroy.yml      # Destruição segura do ambiente

Pipelines CI/CD
1. Build & Push do Runtime (ARM64)

Utiliza Docker Buildx

Constrói a imagem para linux/arm64

Realiza o push diretamente para Amazon ECR

Gatilho manual ou acionado pela branch main

2. Setup do Ambiente com Terraform

Executa terraform init / plan / apply

Cria ou atualiza:

Repositório ECR

Roles e policies IAM

Runtime do Bedrock AgentCore

Gatilho em alterações no diretório infra/

3. Destruição do Ambiente (Manual & Segura)

Gatilho manual

Requer confirmação explícita (DESTROY)

Destrói totalmente o ambiente

Requisitos

Docker com Buildx habilitado

Conta AWS com Bedrock AgentCore habilitado

Terraform >= 1.6

GitHub Actions (para CI/CD)

Segurança e Melhores Práticas

Nenhum arquivo de estado do Terraform é versionado no Git

O arquivo .terraform.lock.hcl é versionado para garantir reprodutibilidade

Secrets armazenados de forma segura no GitHub Actions

Forçamos ARM64 para compatibilidade com o AgentCore

Pipelines de infraestrutura e build completamente desacopladas

Exemplo de Invocação do Runtime
{
  "prompt": "Explique por que os desertos estão comumente localizados próximos aos 30 graus de latitude."
}


O agente responde com explicações estruturadas, factuais e específicas do domínio, sem dados inventados.

Melhorias Futuras

Gateway do AgentCore (exposição de API REST)

Suporte multi-ambiente (dev / prod)

OIDC para CI/CD (sem chaves AWS estáticas)

Ferramentas geográficas (coordenadas, dados climáticos, fusos horários)

Painéis de observabilidade e métricas

Autor

Desenvolvido como um projeto de portfólio DevOps + Generative AI, demonstrando:

Infraestrutura como Código

Runtimes de IA nativos na nuvem

Pipelines CI/CD seguras e escaláveis

Decisões de design voltadas para produção

Licença

Este projeto é fornecido para fins educacionais e demonstração profissional.