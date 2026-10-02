# ERP Demo — API de catálogo e assistente local

**Leonardo Briquezi**  
GitHub: https://github.com/leobrqz  
LinkedIn: https://www.linkedin.com/in/leonardobri

Respostas em PDF: [leonardo_briquezi_respostas_demo.pdf](./leonardo_briquezi_respostas_demo.pdf).

Aplicação de demonstração para catálogo e estoque, com API FastAPI, PostgreSQL, cache e filas Redis, interface web e consultas em linguagem natural por ferramentas MCP.

O enunciado numera as questões como 1, 2, 3, 4, 6, 7, 8, 9, 10 e 11. Mantive a numeração original e não criei uma Questão 5.

## Executar

Execute na raiz do projeto. No Windows:

    .\setup.ps1

O script prepara o `.env` quando necessário, constrói as imagens, inicia os serviços, aplica as migrações e executa o seed. As credenciais do administrador ficam em `ADMIN_USERNAME` e `ADMIN_PASSWORD` no `.env`.

Para habilitar o modelo local:

    .\setup.ps1 -EnableLocalAI

Isso inicia o perfil `ai` e baixa o MiniCPM5-2B Q4_K_M (~1,56 GB) para o volume `model_cache`. Depois do primeiro download, a inferência é local via `llama.cpp`; não há API externa de LLM nem token do Hugging Face.

No macOS/Linux, prepare o `.env` e inicie o Compose:

    cp .env.example .env
    docker compose up --build -d

Antes de subir os serviços, defina credenciais próprias no `.env` e mantenha `DATABASE_URL` consistente com `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`.

Endereços locais:

    Interface: http://localhost:8080
    API e Swagger: http://localhost:8000/docs
    Prontidão: http://localhost:8000/health/ready

Para autenticar no Swagger, use `POST /api/v1/auth/token` com os valores de `ADMIN_USERNAME` e `ADMIN_PASSWORD` do `.env` e informe o JWT em **Authorize**.

Operação:

    docker compose logs -f api
    docker compose down

## Serviços e pastas

O Compose inicia cinco serviços: interface Nginx, API, PostgreSQL, Redis e worker RQ. API e worker compartilham a imagem do projeto. O perfil opcional `ai` adiciona o servidor local `model-server`.

    app/api/          Rotas HTTP e dependências de autenticação
    app/ai/           Agente LangChain, ferramentas MCP e modo determinístico opcional
    app/core/         Configuração, segurança e logging
    app/db/           Sessões SQLAlchemy e cliente Redis
    app/models/       Entidades PostgreSQL
    app/repositories/ Consultas de persistência
    app/schemas/      Contratos Pydantic de entrada e saída
    app/services/     Regras de aplicação, cache, fila e integração
    app/workers/      Tarefas executadas pelo RQ
    frontend/         Interface estática, Nginx e proxy para a API
    migrations/       Histórico Alembic
    Dockerfile        Imagem multi-stage, processo sem root
    docker-compose.yml Interface, API, PostgreSQL, Redis, worker e servidor de modelo opcional
    setup.ps1         Gera credenciais locais e automatiza build e inicialização no Windows

A interface permite entrar com o usuário criado pelo seed, consultar os produtos e conversar em linguagem natural com o agente sobre o catálogo. Ela é servida pelo Nginx no container `frontend`, que encaminha chamadas autenticadas à API pela rede do Compose.

## API implementada

| Método | Rota | Acesso | Uso |
| --- | --- | --- | --- |
| POST | /api/v1/auth/token | Público | Recebe usuário e senha como formulário e emite JWT |
| POST | /api/v1/products | Admin | Cria produto |
| GET | /api/v1/products | Autenticado | Lista com paginação, nome, preço e estoque baixo |
| GET | /api/v1/products/{id} | Autenticado | Lê um produto |
| PATCH | /api/v1/products/{id} | Admin | Atualiza campos informados |
| DELETE | /api/v1/products/{id} | Admin | Exclui produto |
| GET | /api/v1/alerts/low-stock | Autenticado | Lista alertas abertos de estoque baixo |
| GET | /api/v1/erp/snapshot | Autenticado | Agrega três serviços simulados em paralelo |
| POST | /api/v1/ai/ask | Autenticado | Consulta produtos em linguagem natural e retorna JSON |
| POST | /api/v1/ai/ask/stream | Autenticado | Transmite parágrafos da resposta por Server-Sent Events |
| GET | /health/live | Público | Verifica se o processo está vivo |
| GET | /health/ready | Público | Verifica acesso ao PostgreSQL e Redis |

### Obter um token

    curl -X POST http://localhost:8000/api/v1/auth/token \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=admin&password=change-this-local-demo-password"

Use o valor de access_token nas próximas chamadas:

    curl "http://localhost:8000/api/v1/products?page=1&page_size=10&low_stock=10" \
      -H "Authorization: Bearer SEU_TOKEN"

### Consultar o agente

    curl -X POST http://localhost:8000/api/v1/ai/ask \
      -H "Authorization: Bearer SEU_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"question\":\"Quais produtos estão com estoque abaixo de 10 unidades?\"}"

Com `AI_PROVIDER=local`, MiniCPM5-2B interpreta a intenção em linguagem natural e seleciona ferramentas MCP de leitura. Não há exigência de palavras ou formatos específicos. A resposta JSON contém a pergunta, a ferramenta selecionada, os dados retornados e o provedor. A interface usa `/api/v1/ai/ask/stream` e recebe respostas em blocos de parágrafo. Quantidades de produtos e resultados de consultas são montados a partir dos dados retornados pelas ferramentas. `AI_PROVIDER=rules` mantém um modo determinístico simples para executar sem o modelo local.

### Agregação resiliente

    curl "http://localhost:8000/api/v1/erp/snapshot?timeout_ms=250" \
      -H "Authorization: Bearer SEU_TOKEN"

As fontes de estoque, financeiro e clientes são mocks locais. Cada uma tem timeout e uma tentativa de retry independentes. Para observar degradação parcial, use um timeout pequeno, como timeout_ms=1.

## Dados fictícios

O seed em app/seed.py cria somente dados inventados:

- admin / admin@example.test, com senha definida em ADMIN_PASSWORD no .env;
- Café especial, R$ 38,90, estoque 6;
- Caneca térmica, R$ 59,90, estoque 24;
- Caderno pontilhado, R$ 32,50, estoque 3;
- Luminária de mesa, R$ 119,00, estoque 12.

Os três serviços agregados também devolvem valores fictícios escritos em app/services/erp_aggregate.py. Nenhum dado real de cliente ou empresa é usado.

## Respostas da prova

### Parte 1 — Arquitetura e organização

#### Questão 1 — Serviços e comunicação

Eu separaria os serviços por responsabilidade de negócio. O serviço de Produtos e Estoque seria dono do catálogo, saldo e movimentações; Pedidos coordenaria o ciclo do pedido; Financeiro continuaria dono de cobranças e recebimentos; Clientes continuaria dono dos dados cadastrais. Cada serviço manteria seu próprio banco e publicaria contratos estáveis, para que uma mudança interna não obrigasse os outros módulos a conhecerem suas tabelas.

Usaria REST para operações que precisam de resposta imediata, como validar se um cliente existe ou consultar o preço atual antes de aceitar um pedido. Usaria eventos e filas para efeitos que podem terminar depois, como notificar estoque baixo, atualizar relatórios e propagar uma venda confirmada. Eventos precisam de identificador, versão, data, produtor e chave de idempotência. Para não perder evento entre a transação do PostgreSQL e o broker, em produção eu adotaria transactional outbox e consumidores idempotentes.

PostgreSQL seria a fonte de verdade dos dados transacionais, com constraints para invariantes como preço e quantidade não negativos. Redis serviria para cache curto de leituras, rate limiting e filas quando o padrão operacional justificar. Não usaria cache ou lock distribuído como substituto de transação ou constraint no banco. Para operações de estoque concorrentes, a atualização seria atômica no PostgreSQL; um lock Redis só entraria se houvesse uma necessidade demonstrada e com expiração e recuperação bem definidas.

Um API Gateway como Kong centralizaria entrada, roteamento, TLS, autenticação de borda, rate limiting e políticas comuns. A autorização de negócio e as validações continuariam nos serviços, para não transformar o gateway em um serviço monolítico de regras.

Minha experiência prática com AWS é limitada. Conheço opções como ECS/Fargate para contêineres e RDS para PostgreSQL, mas não tenho profundidade para definir sozinho a arquitetura e a operação. Eu validaria mensageria, cache e observabilidade conforme os requisitos e com apoio de alguém experiente na plataforma.

Instrumentaria logs estruturados com request_id/trace_id, métricas Prometheus e tracing distribuído com OpenTelemetry, apresentados em Grafana. No ERP priorizaria latência p95/p99 e taxa de erro das rotas, disponibilidade e conexões do PostgreSQL, idade e tamanho das filas, retries e dead letters, falhas em integrações financeiras e divergências entre estoque reservado e disponível. Logs não devem registrar senhas, tokens nem dados pessoais desnecessários.

#### Questão 2 — Organização FastAPI

A estrutura desse projeto segue uma arquitetura em camadas, com dependências apontando para serviços de aplicação e repositórios, em vez de concentrar regras nas rotas:

    app/api, app/schemas       HTTP e contratos Pydantic
    app/services               casos de uso e regras
    app/repositories, models   consultas e persistência SQLAlchemy
    app/db, app/core           infraestrutura, configuração e segurança
    app/ai, app/workers         agente MCP e tarefas RQ
    migrations                 histórico versionado do schema

Rotas e schemas tratam HTTP; serviços coordenam regras; repositórios isolam a persistência.

### Parte 2 — Assíncrono e concorrência

#### Questão 3 — asyncio, threading e multiprocessing

**asyncio** multiplexa operações de I/O cooperativo em uma thread. É uma boa opção quando há muitas esperas de rede ou banco e as bibliotecas usadas oferecem APIs async. No ERP, eu chamaria simultaneamente os serviços de estoque, financeiro e clientes, como no endpoint da Questão 4.

**threading** é útil para I/O bloqueante quando a biblioteca ainda não tem API assíncrona, ou para manter várias esperas de rede em andamento. No ERP, uma integração antiga de emissão de nota que só oferece cliente bloqueante poderia ser isolada em uma thread para não travar o loop async. O GIL limita ganho de threads para código Python puro que consome CPU.

**multiprocessing** executa trabalho CPU-bound em processos separados e pode usar vários núcleos, pagando o custo de serializar dados e criar processos. No ERP, seria apropriado para consolidar milhões de linhas de um CSV ou gerar um relatório PDF pesado. Esse trabalho também pode ficar em um worker para não ocupar o processo HTTP.

### Parte 3 — API RESTful

#### Questão 4 — Três fontes em paralelo

O endpoint GET /api/v1/erp/snapshot usa asyncio.gather. Estoque, financeiro e cliente são funções mock com latências independentes. Cada chamada passa por timeout próprio e retry simples para timeout/falha transitória. As exceções são convertidas em status por fonte; uma fonte indisponível não remove os resultados das outras. A resposta marca degraded quando houve resultado parcial. Em produção, essas funções seriam clientes HTTP com timeout total, retry limitado com jitter, circuit breaker e métricas.

#### Questão 6 — Produtos e estoque

A API implementa criar, listar, ler, atualizar parcialmente e excluir produto. O schema Pydantic exige nome textual e preço/estoque não negativos. Escolhi SQLAlchemy 2 com Psycopg 3 síncrono pela API de transações e consultas madura e pelo reaproveitamento da mesma camada no worker RQ; as rotas síncronas do FastAPI rodam no thread pool. Reservei asyncio para o endpoint que realmente precisa fazer várias chamadas de I/O em paralelo. PostgreSQL mantém dados duráveis; JWT protege as rotas e o seed cria um usuário admin de demonstração. Listagens aceitam nome, preço mínimo/máximo, quantidade máxima de estoque, página e tamanho limitado.

GET /api/v1/products usa Redis com chaves que incluem um contador de versão e os filtros normalizados. Depois de uma escrita, o contador é incrementado: as novas leituras passam a uma nova versão de chave, e chaves antigas expiram em cinco minutos. Se Redis estiver indisponível, a listagem consulta PostgreSQL e a mutação do produto continua funcionando.

RQ usa o mesmo Redis para enfileirar refresh_low_stock_alert após criar produto ou mudar quantidade. O worker reavalia o saldo e abre, atualiza ou resolve o alerta persistido em PostgreSQL. A tarefa altera estado real do domínio, e GET /api/v1/alerts/low-stock consulta os alertas abertos. Se o Redis falhar entre o commit do produto e o enqueue, a falha fica registrada em log; em produção eu acrescentaria uma transactional outbox para garantir entrega eventual desse trabalho.

### Parte 4 — Docker e entrega

#### Questão 7 — Docker Compose

O Dockerfile usa build multi-stage e executa a API sem root. O Compose inicia Nginx, API, PostgreSQL, Redis e worker; `llama.cpp` fica no perfil opcional `ai`. Nginx encaminha `/api/` e mantém o streaming SSE sem buffering. A API aplica migrações e seed idempotente ao iniciar. Para repetir, use `docker compose exec api alembic upgrade head` ou `docker compose exec api python -m app.seed`. O `.env` local é ignorado pelo Git; `.env.example` contém valores de demonstração.

### Parte 5 — Agente, LLM e MCP

#### Questão 8 — Consulta em linguagem natural

POST /api/v1/ai/ask aceita perguntas em português. Com `AI_PROVIDER=local`, MiniCPM5-2B interpreta o sentido do pedido, escolhe uma ferramenta MCP de leitura e usa seu resultado para responder. A ferramenta e o repositório validam os argumentos e limitam a consulta; o usuário não fornece SQL. Se a intenção estiver ambígua, o assistente pede esclarecimento. Se o modelo estiver indisponível, a aplicação informa a falha sem tentar interpretar o texto com uma lista de frases fixas.

O agente usa LangChain, `ChatOpenAI` apontado para a API compatível do servidor local `llama.cpp` e `MCPAdapter` para descobrir as ferramentas. Os pesos MiniCPM5-2B vêm do repositório oficial do OpenBMB no Hugging Face, em quantização Q4. O modelo tem 2,52B parâmetros e o arquivo quantizado ocupa cerca de 1,56 GB. Não há chamada a OpenAI, Anthropic nem inferência hospedada. O modo determinístico continua disponível ao configurar `AI_PROVIDER=rules`.

Para habilitar o modelo local:

1. Rode `./setup.ps1 -EnableLocalAI` no PowerShell, ou configure `AI_PROVIDER=local` no `.env`.
2. O Compose inicia `model-server`, que baixa `openbmb/MiniCPM5-2B-GGUF:Q4_K_M` do Hugging Face e mantém o arquivo no volume `model_cache`.
3. A API conversa com o modelo em `http://model-server:8080/v1`; `http://localhost:8081/health` mostra quando o serviço está pronto.

Os pesos ficam no volume `model_cache`; o modelo público não exige token do Hugging Face. O timeout padrão é de 60 segundos e pode ser ajustado em `LLM_TIMEOUT_SECONDS`. Se a chamada falhar, a API retorna erro sem interpretar a pergunta por regras de texto.

#### Questão 9 — Plugabilidade, tools, MCP e guardrails

O servidor FastMCP em app/ai/mcp_server.py expõe find_low_stock_products, search_products e list_products. São ferramentas somente de leitura, limitadas e com argumentos tipados. LangChain MCPAdapter descobre essas ferramentas e as converte em ferramentas que create_agent pode usar. A resposta de contagem usa o total consultado no banco, mesmo quando a lista de itens é limitada. A implementação conecta o MCP em memória para manter a demonstração simples; em produção o servidor MCP poderia ficar ao lado dos microsserviços e chamar seus APIs/casos de uso, sem acessar diretamente bancos de outros domínios.

Para conectar um LLM diferente, eu manteria a escolha do provedor em configuração e seguiria o contrato de chat/tool calling do LangChain. O restante do caso de uso recebe ferramentas tipadas e não conhece detalhes do provedor. O modo por regras pode ser selecionado explicitamente para execução sem modelo.

O agente atual não oferece ferramentas de escrita. Se fossem adicionadas, exigiriam autorização de negócio no serviço, validação Pydantic, allowlist de ações e confirmação explícita para operações destrutivas. O resultado do modelo nunca concede permissão; cada chamada é validada com o usuário autenticado. Dados vindos de consultas são tratados como conteúdo, não como instruções.

Eu acompanharia latência, timeouts, falhas, tokens quando disponíveis, ferramentas inválidas e fallback. A inferência local elimina o custo por token de API, mas consome memória e CPU. Registraria métricas e IDs de correlação, sem guardar prompts ou respostas brutos por padrão. Cache só para consultas de leitura, com chave por usuário, filtros e versão dos dados.

O namespace `langchain.mcp` está em beta na documentação atual e pode mudar. Para reduzir impacto em atualizações, eu fixaria a versão e isolaria o adaptador; as ferramentas MCP continuariam atrás de contratos tipados.

### Parte 6 — Perfil

#### Questão 10 — Desenvolver uma frente em Go

Eu começaria pelos requisitos e métricas atuais. Go pode ajudar na ingestão concorrente, mas só migraria após comparar memória, latência p95/p99, throughput e custo operacional com o serviço atual. Se Python async ou uma otimização do banco atingir as metas, não justificaria adicionar outra linguagem. Caso Go seja a melhor opção, faria uma migração gradual, com cancelamento de contexto, erros explícitos, testes e profiling.

### Parte 7 — Portfólio

#### Questão 11 — Projeto representativo

Projeto que escolho destacar: [SmokeShopERP-DataAnalytics](https://github.com/leobrqz/SmokeShopERP-DataAnalytics).

É uma aplicação desktop para acompanhar produtos, vendas, clientes e indicadores de uma tabacaria, feita com Python, PyQt6 e PostgreSQL; Matplotlib e NumPy geram gráficos e análises. Se retomasse o projeto, separaria melhor interface, casos de uso e persistência, adicionaria migrações e testes, e só criaria uma API se houvesse necessidade de múltiplos clientes ou acesso remoto.

## Uso de IA

Codex CLI apoiou a pesquisa, a comparação de alternativas e a geração inicial de partes do código e das respostas. O agente usa MiniCPM5-2B localmente; a aplicação não envia consultas a um LLM hospedado. IA também auxiliou na geração do PDF por meio de um script Python.

## Limitações conhecidas

- As fontes de estoque, financeiro e clientes da agregação são mocks; integrações reais dependem dos contratos dos serviços.
- O agente só tem ferramentas de leitura. A autenticação demonstra um único administrador de seed.
- O enqueue RQ é best-effort; uma transactional outbox não foi implementada.
- Esta versão não inclui uma suíte automatizada de testes.

Repositório: [demo-erp](https://github.com/leobrqz/demo-erp).

## Referências técnicas

- [Documentação FastAPI](https://fastapi.tiangolo.com/)
- [Documentação SQLAlchemy](https://docs.sqlalchemy.org/)
- [Documentação Alembic](https://alembic.sqlalchemy.org/)
- [Documentação RQ](https://python-rq.org/)
- [Integração LangChain com MCP](https://docs.langchain.com/oss/python/langchain/mcp)
- [Model card MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B)
- [MiniCPM5-2B GGUF](https://huggingface.co/openbmb/MiniCPM5-2B-GGUF)
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
