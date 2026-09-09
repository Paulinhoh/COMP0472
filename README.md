# Atividade 1 de Sistemas Operacionais

Projeto de avaliação da disciplina de Sistemas Operacionais, com foco na observação de processos, threads, armazenamento, chamadas de sistema e desempenho de uma aplicação RAG executada localmente com Ollama.

A aplicação utilizada é a trilha B da atividade:

> Ollama + `ollama-local-rag`: RAG textual com LangChain, FAISS e documentos locais.

O modelo de geração utilizado é `granite4.1:3b` e o modelo de embeddings é `nomic-embed-text`.

## Sumário

- [Visão geral](#visão-geral)
- [Estrutura do workspace](#estrutura-do-workspace)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração do Ollama](#configuração-do-ollama)
- [Execução manual do RAG](#execução-manual-do-rag)
- [Documentos de teste](#documentos-de-teste)
- [Execução completa da atividade](#execução-completa-da-atividade)
- [Configurações experimentais](#configurações-experimentais)
- [Arquivos gerados](#arquivos-gerados)
- [Métricas registradas](#métricas-registradas)
- [Chamadas de sistema com strace](#chamadas-de-sistema-com-strace)
- [Resultados atuais](#resultados-atuais)
- [Solução de problemas](#solução-de-problemas)
- [Reprodução limpa](#reprodução-limpa)
- [Limitações](#limitações)

## Visão geral

O fluxo da aplicação é:

```text
arquivos de texto
      |
      v
cópia para dados/documentos_ativos/
      |
      v
chunking com blocos de 300 caracteres e sobreposição de 100
      |
      v
embeddings com nomic-embed-text
      |
      v
índice vetorial FAISS
      |
      v
recuperação dos chunks mais relevantes
      |
      v
prompt com contexto + pergunta
      |
      v
resposta gerada pelo granite4.1:3b via Ollama
```

O Ollama executa localmente. A aplicação Python conversa com o serviço local do Ollama, normalmente na porta `11434`.

## Estrutura do workspace

```text
SO/
├── README.md                         # este arquivo
├── Atividade_1_Sistemas_Operacionais_Classroom.pdf
├── executar_testes.py                # executor da matriz de experimentos
├── documentacao/
│   ├── README.md                     # notas sobre os datasets
│   └── analise_strace.md             # interpretação das chamadas de sistema
├── resultados/                       # saídas dos testes e inventário
│   ├── resultados_atividade_1.csv
│   ├── resumo_atividade_1.csv
│   ├── ambiente_atividade_1.csv
│   ├── processos_atividade_1.csv
│   ├── grafico_atividade_1.svg
│   ├── strace-resumo.txt
│   └── strace-disponibilidade.txt
├── testes_rag/                       # origem dos documentos de teste
│   ├── documentos_pequeno/
│   └── documentos_grande/
└── ollama-local-rag/                 # aplicação RAG
    ├── create_database.py            # criação do índice FAISS
    ├── query_data.py                 # consulta individual
    ├── requirements.txt              # dependências Python
    ├── dados/
    │   └── documentos_ativos/        # cópia usada na indexação atual
    ├── faiss/                        # índice vetorial atual
    │   ├── index.faiss
    │   └── index.pkl
    └── .venv/                        # ambiente virtual Python local
```

As pastas `resultados/` e `documentacao/`, assim como `executar_testes.py`, ficam no nível `SO`, uma pasta acima de `ollama-local-rag`, conforme a organização da entrega.

## Requisitos

- Linux, WSL2 ou ambiente equivalente;
- Python 3.10 ou superior;
- `python3-venv` disponível;
- Ollama instalado e executável;
- aproximadamente 2,3 GB para os modelos locais;
- memória suficiente para executar o modelo de 3B parâmetros;
- os diretórios `testes_rag/documentos_pequeno` e `testes_rag/documentos_grande` presentes.

O ambiente em que os testes foram realizados foi identificado como:

- Ubuntu 26.04.1 LTS;
- WSL2;
- kernel Linux 6.18.40.1;
- CPU Intel Core i5-13420H, 6 threads visíveis;
- aproximadamente 11 GiB de RAM;
- sem GPU NVIDIA detectada;
- Ollama 0.33.3;
- Python 3.14.4.

Os valores completos e a data da coleta estão em [resultados/ambiente_atividade_1.csv](resultados/ambiente_atividade_1.csv).

## Instalação

Todos os comandos abaixo devem ser executados a partir de `/home/paulinhoh/SO`.

### 1. Entrar no workspace

```bash
cd /home/paulinhoh/SO
```

### 2. Criar o ambiente virtual

Se o ambiente ainda não existir:

```bash
python3 -m venv ollama-local-rag/.venv
```

Ativar o ambiente:

```bash
source ollama-local-rag/.venv/bin/activate
```

### 3. Instalar as dependências

```bash
python -m pip install -r ollama-local-rag/requirements.txt
```

As dependências principais são:

- `langchain==0.3.27`;
- `langchain-community==0.3.27`;
- `langchain-ollama==0.3.10`;
- `langchain-text-splitters==0.3.9`;
- `unstructured[md]==0.18.32`;
- `faiss-cpu==1.15.0`.

Também é possível executar os comandos sem ativar o ambiente, usando diretamente:

```bash
ollama-local-rag/.venv/bin/python
```

## Configuração do Ollama

### Verificar instalação

```bash
ollama --version
ollama list
```

### Iniciar o serviço

Em uma sessão de terminal separada, iniciar o serviço se ele ainda não estiver ativo:

```bash
ollama serve
```

Se o serviço já estiver sendo executado pelo sistema, não é necessário iniciar outro processo.

### Baixar os modelos

```bash
ollama pull granite4.1:3b
ollama pull nomic-embed-text
```

Verificar se os modelos estão disponíveis:

```bash
ollama list
```

O modelo `granite4.1:3b` gera as respostas. O modelo `nomic-embed-text` transforma documentos e perguntas em vetores para a busca semântica.

## Execução manual do RAG

### Preparar um conjunto de documentos

O executor completo faz isso automaticamente. Para executar manualmente, copie um dos conjuntos para a pasta ativa:

```bash
rm -rf ollama-local-rag/dados/documentos_ativos
cp -r testes_rag/documentos_pequeno ollama-local-rag/dados/documentos_ativos
```

### Criar o índice FAISS

```bash
ollama-local-rag/.venv/bin/python ollama-local-rag/create_database.py
```

O script lê `.txt` e `.md` da pasta `ollama-local-rag/dados/documentos_ativos`, divide os documentos em chunks e recria `ollama-local-rag/faiss/`.

Parâmetros atuais do chunking:

- tamanho do chunk: 300 caracteres;
- sobreposição: 100 caracteres;
- `add_start_index=True` no metadata;
- embeddings: `nomic-embed-text`.

### Fazer uma consulta

```bash
ollama-local-rag/.venv/bin/python ollama-local-rag/query_data.py "Qual e o prazo para trocar as senhas corporativas?"
```

Alterar a quantidade de chunks recuperados com `--k`:

```bash
ollama-local-rag/.venv/bin/python ollama-local-rag/query_data.py \
  "Explique a politica de trabalho remoto." \
  --k 2
```

A resposta é gerada somente com base no contexto recuperado pelo FAISS.

### Variáveis de caminho opcionais

Os scripts também aceitam caminhos explícitos por variáveis de ambiente:

```bash
RAG_DATA_PATH=/caminho/para/documentos \
RAG_FAISS_PATH=/caminho/para/faiss \
ollama-local-rag/.venv/bin/python ollama-local-rag/create_database.py
```

O executor define essas variáveis automaticamente para cada cenário.

## Documentos de teste

A origem dos documentos é `testes_rag/`, fora do diretório da aplicação.

### Conjunto pequeno

`testes_rag/documentos_pequeno/` contém 5 documentos:

- `faq_suporte.txt`;
- `guia_onboarding.txt`;
- `politica_home_office.txt`;
- `politica_senhas.txt`;
- `procedimento_backup.txt`.

Esse conjunto gerou 27 chunks e é usado na configuração padrão.

### Conjunto grande

`testes_rag/documentos_grande/` contém 15 documentos, incluindo os documentos do conjunto pequeno e materiais adicionais sobre benefícios, reuniões, e-mail, atendimento, segurança, férias, notebook, compras, desligamento e incidentes.

Esse conjunto gerou 83 chunks e é usado nas configurações de concorrência e ajuste de contexto.

### Cópia ativa

Antes de cada configuração, `executar_testes.py`:

1. identifica o dataset em `testes_rag/`;
2. remove `ollama-local-rag/dados/documentos_ativos/`;
3. copia os arquivos do dataset para a pasta ativa;
4. recria o índice FAISS;
5. executa as consultas;
6. registra o nome do dataset e a quantidade de documentos no CSV.

A pasta `dados/documentos_ativos/` é uma área de trabalho. Ela não é a fonte oficial dos testes.

## Execução completa da atividade

O comando recomendado é:

```bash
cd /home/paulinhoh/SO
ollama-local-rag/.venv/bin/python executar_testes.py --rebuild-index
```

O argumento `--rebuild-index` é mantido por compatibilidade e indica a intenção de reconstruir o índice. O executor sempre copia o dataset e recria o índice antes de cada configuração.

Para definir outro arquivo de saída:

```bash
ollama-local-rag/.venv/bin/python executar_testes.py \
  --output resultados/minha_execucao.csv
```

Os arquivos derivados serão criados na mesma pasta do arquivo principal.

Para alterar a quantidade de repetições, mantendo o mínimo exigido de duas:

```bash
ollama-local-rag/.venv/bin/python executar_testes.py --repetitions 3
```

## Configurações experimentais

A matriz implementada atende à exigência de três configurações, dois tamanhos de entrada/carga e pelo menos duas repetições.

| Configuração | Dataset | Concorrência | `k` | Objetivo |
| --- | --- | ---: | ---: | --- |
| `padrao` | `documentos_pequeno` | 1 | 4 | execução sequencial com carga pequena |
| `concorrencia` | `documentos_grande` | 2 | 4 | duas requisições simultâneas com carga grande |
| `ajuste_contexto` | `documentos_grande` | 1 | 2 | reduzir a quantidade de chunks recuperados |

As perguntas utilizadas são:

- curta: `Qual e o prazo para trocar as senhas corporativas?`;
- longa: pergunta que solicita a explicação completa da política de trabalho remoto, incluindo elegibilidade, requisitos técnicos, equipamentos, disponibilidade, segurança, reembolso e acompanhamento.

O cenário concorrente executa duas instâncias de `query_data.py` simultaneamente. Por isso, ele produz quatro linhas para cada tamanho de entrada quando são usadas duas repetições: duas requisições por repetição.

## Arquivos gerados

### `resultados/resultados_atividade_1.csv`

CSV bruto com uma linha por requisição. Contém:

- timestamp;
- configuração e descrição;
- dataset e quantidade de documentos;
- tamanho da entrada;
- número da repetição;
- nível de concorrência;
- quantidade de chunks recuperados;
- status;
- tempo total;
- validade da resposta;
- CPU e RAM observadas;
- quantidade de processos e threads;
- tamanho de documentos e índice;
- modelo, embeddings, Ollama e Python;
- erro, quando existente.

### `resultados/resumo_atividade_1.csv`

Agrega as execuções por configuração e tamanho de entrada, incluindo:

- número de execuções;
- execuções bem-sucedidas;
- taxa de sucesso;
- latência média, mínima e máxima;
- CPU média;
- RAM média;
- threads médias;
- espaço ocupado por documentos e índice.

### `resultados/ambiente_atividade_1.csv`

Inventário do ambiente:

- distribuição Linux;
- kernel;
- CPU e número de threads;
- RAM e swap;
- armazenamento disponível;
- dispositivos de bloco;
- GPU;
- versão do Ollama;
- modelos instalados;
- versão do Python;
- disponibilidade do `strace`;
- tamanho dos documentos e do índice;
- espaço ocupado pelos modelos.

### `resultados/processos_atividade_1.csv`

Snapshot dos processos observados, com PID, PPID, estado, CPU, RAM, threads, comando e argumentos. Os principais processos esperados são:

- `ollama serve`;
- `llama-server` do embedding;
- `llama-server` do modelo de geração;
- processos Python da aplicação.

### `resultados/grafico_atividade_1.svg`

Gráfico com a latência média de cada combinação de configuração e tamanho de entrada.

### `resultados/strace-resumo.txt`

Resumo agregado de chamadas de sistema (`strace -f -c`) obtido durante uma consulta RAG.

### `resultados/strace-disponibilidade.txt`

Registra o caminho do `strace` e o comando para reproduzir a coleta.

## Métricas registradas

| Métrica | Como é obtida | Observação |
| --- | --- | --- |
| Tempo total | `time.perf_counter()` ao redor do subprocesso Python | inclui carregamento do índice, embedding, recuperação e resposta |
| Inicialização | valor `service_already_running` | o Ollama é iniciado antes da medição |
| TTFT | `unavailable_cli_only` | a interface atual aguarda a resposta completa |
| Tokens por segundo | `unavailable_cli_only` | a CLI atual não expõe contagem de tokens |
| CPU | soma do `%CPU` observado por `ps` | amostragem antes/depois da requisição |
| RAM | soma do `%MEM` observado por `ps` | amostragem antes/depois da requisição |
| Processos | contagem dos processos relacionados | `ollama`, `python` e `python3` |
| Threads | soma de `NLWP` | observada pelo `ps` |
| Armazenamento | bytes dos documentos ativos e do índice | não inclui os pesos do modelo nessa coluna |
| Taxa de erro | falhas sobre o total de tentativas | status `ok`, `erro` ou `timeout` |
| Validade | resposta não vazia e processo sem erro | critério operacional simples e explícito |

## Chamadas de sistema com strace

O resumo foi coletado com `strace -f -c` sobre uma consulta RAG. As chamadas mais relevantes observadas foram:

- `futex`: sincronização entre threads;
- `newfstatat`, `openat`, `read`, `close` e `fstat`: acesso a arquivos, dependências, documentos e índice;
- `mmap`: mapeamento de memória para bibliotecas e dados;
- `recvfrom`: recebimento de dados da comunicação local com o Ollama.

Para reproduzir, usando o caminho local disponível neste ambiente:

```bash
cd /home/paulinhoh/SO
/tmp/strace-local/extracted/usr/bin/strace -f -c \
  -o resultados/strace-resumo.txt \
  ollama-local-rag/.venv/bin/python \
  ollama-local-rag/query_data.py \
  "Qual e o procedimento para reportar um incidente de seguranca?" --k 4
```

Em uma instalação normal do sistema, o comando equivalente é:

```bash
sudo apt-get install strace
strace -f -c -o resultados/strace-resumo.txt \
  ollama-local-rag/.venv/bin/python \
  ollama-local-rag/query_data.py "pergunta" --k 4
```

## Resultados atuais

A execução registrada contém:

- 16 execuções mensuráveis;
- 16 respostas com status `ok`;
- perguntas curta e longa;
- duas repetições por cenário;
- dataset pequeno com 5 documentos na configuração padrão;
- dataset grande com 15 documentos nas configurações de concorrência e ajuste de contexto;
- índice pequeno com 27 chunks;
- índice grande com 83 chunks.

Os valores agregados podem ser consultados em [resultados/resumo_atividade_1.csv](resultados/resumo_atividade_1.csv).

## Solução de problemas

### `ModuleNotFoundError`

Ative o ambiente virtual ou use o interpretador completo:

```bash
ollama-local-rag/.venv/bin/python -m pip install -r ollama-local-rag/requirements.txt
```

### `ollama: command not found`

Instale o Ollama seguindo a documentação oficial e confirme:

```bash
ollama --version
```

### Modelo não encontrado

```bash
ollama pull granite4.1:3b
ollama pull nomic-embed-text
```

### Falha de conexão com Ollama

Inicie o serviço:

```bash
ollama serve
```

### FAISS inexistente ou incompatível

Recrie o índice:

```bash
cd /home/paulinhoh/SO
ollama-local-rag/.venv/bin/python executar_testes.py --rebuild-index
```

### Dataset não encontrado

Confirme os diretórios:

```bash
find /home/paulinhoh/SO/testes_rag -maxdepth 2 -type f | sort
```

Os nomes esperados são exatamente `documentos_pequeno` e `documentos_grande`.

### Execução muito lenta

A geração ocorre localmente em CPU quando não há GPU disponível. Verifique os processos:

```bash
ps -eo pid,ppid,stat,pcpu,pmem,nlwp,comm,args --sort=-pcpu
```

Também é possível reduzir a quantidade de repetições para uma verificação rápida, mas a entrega da atividade deve usar pelo menos duas:

```bash
ollama-local-rag/.venv/bin/python executar_testes.py --repetitions 2
```

### Permissão ou falta de espaço

Verifique:

```bash
df -h /home/paulinhoh/SO
free -h
ollama list
```

## Reprodução limpa

Para reconstruir o ambiente Python sem apagar documentos ou resultados:

```bash
cd /home/paulinhoh/SO
rm -rf ollama-local-rag/.venv
python3 -m venv ollama-local-rag/.venv
ollama-local-rag/.venv/bin/python -m pip install -r ollama-local-rag/requirements.txt
ollama pull granite4.1:3b
ollama pull nomic-embed-text
ollama-local-rag/.venv/bin/python executar_testes.py --rebuild-index
```

Para limpar somente a cópia ativa e o índice, deixando a fonte dos datasets intacta:

```bash
rm -rf ollama-local-rag/dados/documentos_ativos ollama-local-rag/faiss
ollama-local-rag/.venv/bin/python executar_testes.py --rebuild-index
```

Para preservar os resultados atuais antes de uma nova rodada:

```bash
cp -a resultados "resultados_backup_$(date +%Y%m%d_%H%M%S)"
```

## Limitações

- TTFT e tokens por segundo não são expostos pela interface de consulta atual.
- O tempo de inicialização do serviço Ollama não é medido por requisição; o serviço é considerado previamente iniciado.
- CPU e RAM são amostragens por `ps`, não um perfil contínuo de todo o período.
- O critério de validade verifica resposta não vazia e ausência de erro, mas não substitui uma avaliação manual da correção factual.
- Uma consulta sobre o prazo de troca de senhas encontrou o documento correto, mas algumas configurações de `k` não recuperaram o chunk que contém os 90 dias; esse caso demonstra que a taxa de sucesso operacional não mede, sozinha, a qualidade factual da resposta.
- O índice `faiss/` representa o último dataset processado. No estado atual, ele corresponde ao último cenário executado, `documentos_grande`.
- A coleta de `strace` depende da disponibilidade da ferramenta e de permissões do ambiente.
- Os documentos são sintéticos/públicos para fins acadêmicos; não adicionar segredos, tokens, dados pessoais ou arquivos confidenciais.

## Arquivos de referência

- [PDF da atividade](Atividade_1_Sistemas_Operacionais_Classroom.pdf)
- [Executor dos testes](executar_testes.py)
- [Aplicação RAG](ollama-local-rag/README.md)
- [Criação do índice](ollama-local-rag/create_database.py)
- [Consulta individual](ollama-local-rag/query_data.py)
- [Documentação dos datasets](documentacao/README.md)
- [Análise do strace](documentacao/analise_strace.md)
