# Radar de Licitações do Pará

As compras públicas do estado, do jeito que o governo publica — só que possível de filtrar.

Consulte as licitações do Pará por município, prazo, valor e objeto. Os dados vêm do
**PNCP** (Portal Nacional de Contratações Públicas), a fonte oficial, e são recolhidos
por um job diário.

🔗 **[Abrir o site](https://pedrozxx.github.io/radar-licitacoes-pa/)**

[![CI](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/ci.yml/badge.svg)](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/ci.yml)
[![Pages](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/pages.yml/badge.svg)](https://github.com/pedrozxx/radar-licitacoes-pa/actions/workflows/pages.yml)

---

## Por que este projeto existe

Quem vende para o poder público precisa achar o edital **antes de o prazo fechar**. O
PNCP publica tudo, mas a consulta oficial exige escolher uma modalidade por vez, não
filtra por município e não avisa o que encerra amanhã. Este site resolve exatamente isso.

## O problema técnico interessante

A parte difícil não é a tela — é a origem. Medindo a API do PNCP contra o serviço real,
e não pela documentação:

| O que a origem faz | Como o projeto lida |
| --- | --- |
| `codigoModalidadeContratacao` é **obrigatório**: não existe "trazer tudo" | O coletor varre modalidade por modalidade e junta, deduplicando por `numeroControlePNCP` |
| **Limita requisições** — e o limite tem duas caras: `429` e, pior, `200` com corpo **HTML** | O cliente checa o `content-type` antes de interpretar. Sem isso, o limite chega ao usuário como erro de parse, sem pista da causa |
| É **lenta**: 4,4 s numa consulta de 10 dias | Cache de 15 min no servidor + snapshot estático servido ao navegador |
| **Cai**. Durante o desenvolvimento devolveu `504` em toda requisição por vários minutos | A coleta saiu do caminho da requisição: um job diário grava um JSON e o site lê esse arquivo. O site continua de pé com o PNCP fora do ar |
| O tempo total é **imprevisível** | `buscar()` recebe um orçamento de tempo. Estourou, devolve o que tem e marca `truncado` — a interface avisa que a lista está incompleta em vez de fingir que é a lista inteira |

O detalhe que mais me custou: **o limite de requisições responde `200 OK`**. Um
`response.json()` direto quebra com erro de parse e não diz por quê. Está travado em
teste, em `tests/test_pncp.py`.

## Decisões que valem explicar

**Por que existe backend, se o site é estático?** Três motivos concretos: o PNCP não
envia `Access-Control-Allow-Origin`, então o navegador não pode chamá-lo direto; o
limite de requisições corta quem insiste, e um intermediário com cache atende muitos
visitantes com uma consulta só; e a junção das modalidades e a limpeza dos campos
precisam acontecer em um lugar só, não espalhadas pelos componentes.

**Por que os dados são um arquivo estático?** Porque a origem é lenta e instável. Um
job agendado pode esperar e pedir devagar; um usuário olhando para a tela, não. O site
abre instantaneamente e sobrevive à queda do PNCP.

**Por que não usei uma biblioteca de data fetching?** É uma requisição de um arquivo
estático, no carregamento. `useEffect` com cancelamento resolve. Acrescentar
TanStack Query aqui seria peso sem função.

**Ausência não é zero.** O PNCP manda `null` e `0` para "valor não informado". Tratar
como zero faria a tela exibir "R$ 0,00", como se existisse contrato de graça, e ainda
somaria errado. Vira `null`, aparece como "não informado", e o total diz **quantos
registros entrou na conta**: `soma 169 de 174 — o PNCP não informou valor em 5`.

**Uma cor só de estado.** O validador de paleta acusou ΔE 12,4 entre o âmbar e o
vermelho que eu tinha escolhido — abaixo do piso de 15, difíceis de separar mesmo com
visão de cor completa. Em vez de trocar o tom, tirei a cor: só o urgente é colorido, e
todo estado de prazo traz o texto por extenso. Ver [`DESIGN.md`](DESIGN.md).

## Stack

**Front** React 19 · TypeScript (`strict`, `noUncheckedIndexedAccess`) · Vite · CSS puro com custom properties  
**Back** Python 3.12 · FastAPI · httpx  
**Testes** Vitest (39) · pytest (39)  
**CI** GitHub Actions — tipos, lint, testes e build a cada push  
**Deploy** GitHub Pages (site estático, publicado por Action a cada push)

## Rodando localmente

```bash
git clone https://github.com/pedrozxx/radar-licitacoes-pa.git
cd radar-licitacoes-pa

# Back
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn api.index:app --reload --port 8778

# Front, em outro terminal
cd web && npm install && npm run dev
```

Para atualizar os dados na mão:

```bash
python scripts/coletar.py --dias 30 --uf PA
```

## Testes

```bash
pytest -q                 # back
cd web && npm test        # front
```

Nenhum teste toca a rede — as respostas do PNCP são simuladas com `respx`. Um teste que
depende de origem externa instável falha por motivo errado e ensina o time a ignorar CI
vermelho.

O que eles cobrem é o que quebra de verdade: valor zerado virando `null`, prazo ausente
que **não** pode virar "aberto", registro repetido entre modalidades, resultado truncado
que precisa vir marcado, o `200` com HTML do limite de requisições, e as duas regressões
que só apareceram com dado real — a ordenação por prazo que punha o edital vencido há
495 dias no topo de "prazo mais próximo", e a data sem hora que recuava um dia em
fuso negativo.

## Estrutura

```
api/
  index.py            endpoints FastAPI
  _core/
    pncp.py           cliente: limite, orçamento de tempo, nova tentativa
    normalize.py      PNCP cru -> formato da interface (funções puras)
    cache.py          cache em memória com expiração
scripts/
  coletar.py          job diário; grava o snapshot
web/
  src/lib/            tipos, formatação e filtro (funções puras, testadas)
  src/components/     KPIs, ranking, filtros, tabela, estados
  public/dados/       snapshot publicado
DESIGN.md             sistema de design — tokens, paleta e o que é proibido
```

## Limites conhecidos

- Cobre o **Pará**. A API aceita outras UFs; o site ainda não expõe a escolha.
- O coletor busca até 300 registros por modalidade. Quando corta, a interface avisa.
- O PNCP publica registro com data de encerramento **anterior** à de publicação. O
  site mostra como veio, sem corrigir — inventar data seria pior.

## Licença

MIT. Ver [`LICENSE`](LICENSE).

## Autor

**Pedro Augusto Darolt** — [GitHub](https://github.com/pedrozxx) · 
[LinkedIn](https://www.linkedin.com/in/pedro-darolt/) · pedrocod.dev@gmail.com

Projeto independente, sem vínculo com qualquer órgão público.
