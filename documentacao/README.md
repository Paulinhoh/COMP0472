# Documentacao da atividade

A origem dos documentos de teste fica fora deste projeto, em `../testes_rag`.
O script `executar_testes.py` copia o conjunto selecionado para
`dados/documentos_ativos/`, recria o índice FAISS e só então executa as consultas.

## Conjuntos usados

- `documentos_pequeno`: 5 documentos, usado na configuração padrão.
- `documentos_grande`: 15 documentos, usado nas configurações de concorrência e ajuste de contexto.

Os resultados ficam em `resultados/`. O arquivo bruto contém uma linha por
requisição e o resumo agrega latência, CPU, RAM, threads e taxa de sucesso.