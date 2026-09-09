# Analise das chamadas de sistema

A consulta RAG foi executada com `strace -f -c` e o resultado está em
`resultados/strace-resumo.txt`.

- `futex`: sincronização entre threads do processo Python e bibliotecas usadas durante a consulta.
- `newfstatat`, `openat`, `read`, `close` e `fstat`: acesso aos arquivos Python, dependências, documentos ativos e arquivos do índice FAISS.
- `mmap`: mapeamento de regiões de memória usadas por bibliotecas e dados do índice durante a execução.
- `recvfrom`: recebimento de dados da comunicação local com o serviço Ollama.

O resumo foi produzido com a cópia local de `strace` em
`/tmp/strace-local/extracted/usr/bin/strace`, sem alterar a instalação do sistema.