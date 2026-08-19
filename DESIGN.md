# Design System: Radar de Licitações do Pará

Documento normativo. Nenhuma linha de markup ou CSS deve contrariar o que está aqui.
Os valores desta página existem como custom properties em `web/src/styles/tokens.css` —
**nunca escreva um hex direto no componente.**

## 1. Tema visual e atmosfera

**Diário Oficial.** A referência é um registro público bem composto: tipografia forte,
fios de separação em vez de caixas flutuando, e o número tratado como protagonista.
A ferramenta lida com dinheiro público e prazo que expira — precisa parecer instrumento
de consulta, não produto de startup.

- **Densidade 8 (Cockpit).** O usuário veio ler muitos registros de uma vez. Por ser
  densidade acima de 7, **todo número é monoespaçado e tabular**, sem exceção.
- **Variância 5.** Assimetria onde ajuda a leitura (filtros à esquerda, resultado à
  direita), simetria onde a comparação exige alinhamento. Não é peça de portfólio:
  legibilidade ganha de gesto gráfico.
- **Movimento 3 (Contido).** Sem animação de entrada em lista, sem contador subindo.
  A transição existe só para explicar mudança de estado — filtro aplicado, item
  carregando. Prazo que fecha hoje não precisa piscar para ser urgente.

## 2. Paleta e papéis

Um único acento. Os tons de urgência **não são acento** — são estado semântico e só
aparecem ligados a prazo.

### Claro

- **Papel** (`#FBFAF8`) — fundo da página, off-white levemente quente
- **Superfície** (`#FFFFFF`) — fundo de tabela e de painel de filtro
- **Tinta** (`#17181A`) — texto primário, títulos, valores
- **Tinta Fraca** (`#6B6E76`) — rótulo, metadado, texto secundário
- **Fio** (`#E4E2DD`) — divisória de 1px, borda de campo
- **Verde Tocantins** (`#17694C`) — **acento único**: link, estado ativo, anel de foco

### Escuro

- **Papel** (`#121316`) · **Superfície** (`#191B1F`) · **Tinta** (`#EDEDEA`)
- **Tinta Fraca** (`#9A9DA5`) · **Fio** (`#2A2D33`) · **Verde Tocantins** (`#37B07C`)

### Estado de prazo (semântico, não decorativo)

- **Âmbar** (`#9E6500` claro / `#D99A2B` escuro) — **a única cor de estado**:
  encerra em 3 dias ou menos
- **Neutro** — todo o resto usa Tinta Fraca, e "encerrado" ainda mais apagado.
  Se tudo é colorido, nada é urgente.

> Havia um segundo tom (terra `#A33A2E`) para "encerrado". Foi removido depois de
> medir: o validador de paleta acusou **ΔE 12,4 entre ele e o âmbar em visão
> normal** — abaixo do piso de 15, difíceis de separar mesmo enxergando todas as
> cores, e rótulo de texto não desculpa esse caso. O âmbar também desceu de
> `#A66A00` para `#9E6500` porque o anterior dava 4,48:1 sobre branco e reprovava
> no mínimo de 4,5:1 para texto.

Contraste mínimo obrigatório: **4.5:1** para texto, **3:1** para borda de campo e ícone.
Cor nunca é o único portador de informação — todo estado de prazo traz também rótulo em
texto ("encerra em 2 dias").

## 3. Tipografia

- **Texto e títulos:** `Geist` — hierarquia por peso e cor, não por tamanho gigante
- **Números:** `Geist Mono` com `font-variant-numeric: tabular-nums` — valor, data,
  CNPJ, contagem. Coluna de dinheiro **alinhada à direita**, sempre.
- **Escala:** `clamp()` no display; corpo nunca abaixo de `1rem` (16px)
- **Medida:** máximo 65 caracteres por linha em texto corrido
- **Banido:** `Inter`, qualquer serifa (isto é software de consulta), `#000000`

## 4. Componentes

- **Botão** — preenchimento sólido no primário, contorno no secundário. Recuo tátil de
  1px no `:active`. Sem brilho externo, sem gradiente, sem cursor customizado.
- **Tabela de resultado** — o componente central. Sem card, sem sombra: linhas separadas
  por Fio. Cabeçalho fixo ao rolar. Zebra é proibida (polui número); o realce é no
  `:hover` da linha inteira.
- **Filtro** — rótulo **acima** do campo, erro **abaixo**. Anel de foco no acento, 2px,
  com deslocamento. Todo filtro ativo vira um marcador removível acima do resultado,
  para que o usuário nunca esqueça por que a lista está curta.
- **Carregando** — esqueleto com as dimensões exatas das linhas da tabela. **Círculo
  girando é proibido.** A consulta ao PNCP leva segundos; o esqueleto informa quantas
  linhas virão.
- **Vazio** — precisa dizer *por que* está vazio e *o que fazer*: "Nenhuma licitação com
  esses filtros entre 01/08 e 10/08. Amplie o período ou remova o filtro de município."
- **Erro** — a origem falha de verdade (o PNCP devolve HTML quando limita requisição).
  O erro é inline, explica em português o que houve e oferece "tentar de novo".
  Nunca engolir a falha e mostrar lista vazia — [[armadilhas-sentinela-e-cache]].

## 5. Layout

- CSS Grid como base. Nada de `calc()` com porcentagem.
- Contêiner máximo de `1400px`, centralizado, respiro interno generoso.
- Altura cheia com `min-h-[100dvh]`, nunca `h-screen`.
- Nenhum elemento sobrepõe outro. Cada um tem sua faixa.
- **Abaixo de 768px tudo vira coluna única.** Filtro colapsa em painel acionável.
  A tabela vira lista de cartões — tabela larga com rolagem horizontal é falha crítica,
  e o overflow horizontal na página é proibido.
- Alvo de toque mínimo de `44px`.

## 6. Movimento

- Só `transform` e `opacity`. Nunca animar `width`, `height`, `top`, `left`.
- Duração curta (120–200ms), com curva de saída suave.
- `prefers-reduced-motion: reduce` desliga tudo. Obrigatório.

## 7. Proibido

Sem emoji. Sem `Inter`. Sem serifa. Sem `#000000`. Sem brilho neon nem sombra colorida.
Sem gradiente em título. Sem cursor customizado. Sem três cards iguais lado a lado.
Sem "Scroll to explore", seta pulando ou chevron animado. Sem `LABEL // 2026`.
Sem "Elevate", "Seamless", "Unleash", "Next-Gen".

**E o mais importante para este projeto: nenhum número inventado.** Nada de "1.200
licitações monitoradas" ou "98% de precisão" em lugar nenhum. Todo número exibido vem
da resposta do PNCP naquela consulta. Se o dado não veio, a interface diz que não veio.
