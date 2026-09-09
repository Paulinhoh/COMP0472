# Aplicação RAG local

Este diretório contém a aplicação RAG baseada em LangChain, Ollama e FAISS usada na Atividade 1 de Sistemas Operacionais.

A documentação completa do workspace, incluindo instalação, datasets, experimentos, métricas, processos, `strace` e solução de problemas, está em:

- [README principal da atividade](../README.md)

## Arquivos da aplicação

- `create_database.py`: lê os documentos ativos e recria o índice FAISS;
- `query_data.py`: recupera contexto e consulta o modelo local;
- `requirements.txt`: dependências Python;
- `dados/documentos_ativos/`: cópia de trabalho do dataset usado na última indexação;
- `faiss/`: índice vetorial atual;
- `.venv/`: ambiente virtual Python local.

## Execução rápida

A partir da pasta `SO`:

```bash
ollama-local-rag/.venv/bin/python executar_testes.py --rebuild-index
```

Para consultar manualmente o índice atual:

```bash
ollama-local-rag/.venv/bin/python ollama-local-rag/query_data.py \
  "Qual e o prazo para trocar as senhas corporativas?"
```

Para recriar somente o índice dos documentos atualmente copiados:

```bash
ollama-local-rag/.venv/bin/python ollama-local-rag/create_database.py
```

Os datasets oficiais ficam em `../testes_rag/documentos_pequeno` e `../testes_rag/documentos_grande`. O executor principal, os resultados e a documentação da atividade ficam um nível acima deste diretório.
