# Radar de Licitações do Pará

Consulta de compras públicas do Pará a partir do PNCP, com filtros por município, texto e situação do prazo. Projeto independente, sem vínculo com órgãos públicos.

[Demonstração](https://pedrozxx.github.io/radar-licitacoes-pa/) · [CI](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/ci.yml) · [Coleta](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/coletar.yml)

## Problema e escopo

A aplicação reúne registros de diferentes modalidades de contratação e apresenta prazo, objeto, órgão e valor estimado. Valores ausentes ficam como “não informado”; resultados parciais devem ser identificados como incompletos. A data de coleta aparece no site: os dados não são uma consulta em tempo real.

## Como funciona

1. `scripts/coletar.py` consulta o PNCP, modalidade por modalidade, com orçamento de tempo e limite de páginas.
2. `api/_core/normalize.py` normaliza os campos, classifica prazos e remove duplicatas com identificador.
3. O coletor grava `web/public/dados/licitacoes-pa.json`, incluindo falhas e truncamento. Uma coleta vazia preserva o arquivo anterior.
4. O GitHub Pages publica o front-end React, que lê esse JSON e aplica os filtros no navegador.

A API FastAPI é uma forma alternativa de consultar os dados. **O site estático não precisa de um backend em execução e não chama essa API.** O cache em memória dura 15 minutos por instância; resultados incompletos não são armazenados nele.

## Stack e requisitos

- Python 3.12, FastAPI, httpx e Uvicorn.
- Node.js 22, React 19, TypeScript e Vite.
- pytest/respx no Python; Vitest/Testing Library no front-end.
- GitHub Actions para testes, coleta e publicação.

Não são necessárias chaves de API nem arquivo `.env` para executar o projeto.

## Executar o site localmente

```bash
git clone https://github.com/pedrozxx/radar-licitacoes-pa.git
cd radar-licitacoes-pa/web
npm ci
npm run dev
```

Abra o endereço indicado pelo Vite. O snapshot versionado permite abrir o site sem consultar o PNCP. Alterar o backend não muda esse arquivo automaticamente.

## Executar a API (opcional)

Na raiz do repositório:

```bash
python -m venv .venv
```

Ative com `source .venv/bin/activate` no Linux/macOS ou `.venv\Scripts\Activate.ps1` no PowerShell. Em seguida:

```bash
python -m pip install -r requirements-dev.txt
python -m uvicorn api.index:app --reload --port 8778
```

Documentação interativa: <http://127.0.0.1:8778/api/docs>.

| Endpoint | Finalidade |
| --- | --- |
| `GET /api/health` | Saúde do processo |
| `GET /api/modalidades` | Modalidades aceitas |
| `GET /api/municipios` | Municípios do Pará, via IBGE e cache |
| `GET /api/licitacoes?dias=14&uf=PA&modalidades=6,8,9` | Consulta normalizada; filtros e ordenação na documentação da API |

Falhas de limite do PNCP viram HTTP 429; indisponibilidade vira 503. A API valida a janela de 1 a 31 dias. Ela não oferece autenticação, persistência em banco ou escrita de contratos.

## Atualizar os dados

Com o ambiente Python ativado, na raiz:

```bash
python scripts/coletar.py --dias 30 --uf PA
```

O comando usa a rede e sobrescreve o snapshot local apenas quando recebe registros. Para um teste isolado, acrescente `--saida web/public/dados/coleta-teste.json`.

No GitHub, `coletar.yml` agenda a coleta para 09:00 UTC. O horário efetivo depende da fila do Actions. O workflow de Pages também acompanha a conclusão bem-sucedida da coleta: um commit feito com `GITHUB_TOKEN` não dispara sozinho outro workflow por `push`.

## Testes e verificações

Na raiz, com o ambiente Python ativado:

```bash
python -m pytest -q
python -m ruff check .
```

No diretório `web`:

```bash
npm ci
npm test
npm run typecheck
npm run build
```

Os testes simulam as respostas externas. Cobrem normalização, deduplicação, cache, limite retornado como HTTP 429 ou HTML, resultados parciais, contrato HTTP, preservação do snapshot e exibição do aviso de coleta incompleta. A quantidade de testes deve ser consultada na execução, evitando números fixos desatualizados neste README.

## Estrutura

```text
api/index.py                 endpoints FastAPI
api/_core/                   cliente PNCP, cache e normalização
scripts/coletar.py           coleta e gravação do snapshot
tests/                       testes Python
web/src/components/          apresentação
web/src/lib/                 filtros, tipos e formatação
web/public/dados/             snapshot publicado
.github/workflows/           CI, coleta e Pages
```

## Decisões e limitações

- **Snapshot estático:** permite consultar os últimos dados publicados quando a origem está indisponível. Exige monitorar a data de coleta e a publicação.
- **Consulta serial:** evita pressionar a origem com várias modalidades ao mesmo tempo; aumenta o tempo de coleta.
- **Dados incompletos:** o teto é de seis páginas de 50 registros por modalidade no coletor. Falhas e cortes precisam permanecer visíveis.
- **Prazos:** a classificação é calculada na coleta e pode ficar desatualizada até a próxima publicação; confirme o edital no PNCP.
- **Cobertura:** o coletor usa as modalidades 6, 8, 9, 4 e 12. Não representa todas as compras públicas possíveis.
- **Filtros:** o site filtra município, texto e situação e ordena por prazo, valor ou publicação. Valor mínimo é parâmetro da API, não um controle da interface.
- **Deploy:** o Pages publica somente o front-end. A configuração de API existente não comprova que exista backend público implantado.

O sistema visual existente está documentado em [DESIGN.md](DESIGN.md).

## Autoria e licença

Pedro Augusto Darolt · [GitHub](https://github.com/pedrozxx) · [LinkedIn](https://www.linkedin.com/in/pedro-darolt/).
Código sob [licença MIT](LICENSE). Os dados têm origem no PNCP; este projeto não substitui a fonte oficial.
