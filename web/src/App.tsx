import { useEffect, useMemo, useState } from 'react'

import { AvisoIncompleto, Erro, Esqueleto, Vazio } from './components/Estados'
import { Filtros } from './components/Filtros'
import { Kpis } from './components/Kpis'
import { RankingOrgaos } from './components/RankingOrgaos'
import { Tabela } from './components/Tabela'
import { filtrar, municipiosDisponiveis, resumirLista } from './lib/filtrar'
import { formatarData, formatarDataHora } from './lib/formatar'
import { FILTROS_INICIAIS, type Filtros as TipoFiltros, type Snapshot } from './lib/types'

// Montado a partir de BASE_URL, e não relativo à URL atual: um visitante que
// chega em /radar-licitacoes-pa (sem barra final) faria o caminho relativo
// resolver para /dados/... e receber 404.
const CAMINHO_DADOS = `${import.meta.env.BASE_URL}dados/licitacoes-pa.json`

const NOMES_MODALIDADE: Record<number, string> = {
  1: 'leilão eletrônico',
  2: 'diálogo competitivo',
  3: 'concurso',
  4: 'concorrência eletrônica',
  5: 'concorrência presencial',
  6: 'pregão eletrônico',
  7: 'pregão presencial',
  8: 'dispensa de licitação',
  9: 'inexigibilidade',
  12: 'credenciamento',
  13: 'leilão presencial',
}

type Estado =
  | { fase: 'carregando' }
  | { fase: 'pronto'; dados: Snapshot }
  | { fase: 'erro'; mensagem: string }

export default function App() {
  const [estado, setEstado] = useState<Estado>({ fase: 'carregando' })
  const [filtros, setFiltros] = useState<TipoFiltros>(FILTROS_INICIAIS)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    let cancelado = false
    setEstado({ fase: 'carregando' })

    fetch(CAMINHO_DADOS, { cache: 'no-cache' })
      .then(async (resposta) => {
        if (!resposta.ok) throw new Error(`arquivo de dados respondeu ${resposta.status}`)
        return (await resposta.json()) as Snapshot
      })
      .then((dados) => {
        if (!cancelado) setEstado({ fase: 'pronto', dados })
      })
      .catch((erro: unknown) => {
        if (cancelado) return
        // A falha vira mensagem na tela, nunca lista vazia: "nenhum resultado"
        // e "não consegui carregar" são coisas diferentes para quem lê.
        setEstado({
          fase: 'erro',
          mensagem:
            erro instanceof Error
              ? `Falha ao ler o arquivo de dados (${erro.message}).`
              : 'Falha desconhecida ao ler o arquivo de dados.',
        })
      })

    return () => {
      cancelado = true
    }
  }, [tentativa])

  const dados = estado.fase === 'pronto' ? estado.dados : null

  const itensFiltrados = useMemo(
    () => (dados ? filtrar(dados.itens, filtros) : []),
    [dados, filtros],
  )

  // Recalculado sobre a lista filtrada, e não reaproveitado do arquivo: exibir
  // o total do snapshot ao lado de uma lista filtrada mostraria ao usuário um
  // número que não corresponde ao que está na tela.
  const resumo = useMemo(() => resumirLista(itensFiltrados), [itensFiltrados])

  const municipios = useMemo(
    () => (dados ? municipiosDisponiveis(dados.itens) : []),
    [dados],
  )

  const temFiltro =
    filtros.municipio !== '' || filtros.busca.trim() !== '' || filtros.status !== 'todas'

  const modalidadesFalhas = (dados?.modalidades_falhas ?? []).map(
    (id) => NOMES_MODALIDADE[id] ?? `código ${id}`,
  )

  return (
    <>
      <a className="pular-para-conteudo" href="#conteudo">
        Pular para os resultados
      </a>

      <header className="cabecalho">
        <div className="envolucro cabecalho-linha">
          <div>
            <h1>Radar de Licitações do Pará</h1>
            <p>
              As compras públicas do estado, do jeito que o governo publica — só
              que possível de filtrar. Dados do Portal Nacional de Contratações
              Públicas.
            </p>
            {dados && (
              <p className="procedencia">
                Período de {formatarData(dados.periodo.inicio)} a{' '}
                {formatarData(dados.periodo.fim)} · coletado em{' '}
                {formatarDataHora(dados.gerado_em)}
              </p>
            )}
          </div>
        </div>
      </header>

      <main id="conteudo" className="envolucro">
        {estado.fase === 'erro' && (
          <div style={{ marginBlock: 'var(--e6)' }}>
            <Erro
              mensagem={estado.mensagem}
              aoTentar={() => setTentativa((n) => n + 1)}
            />
          </div>
        )}

        {estado.fase === 'carregando' && (
          <div style={{ marginBlock: 'var(--e6)' }}>
            <Esqueleto />
          </div>
        )}

        {dados && (
          <>
            <Kpis resumo={resumo} />

            {modalidadesFalhas.length > 0 && (
              <div style={{ marginBottom: 'var(--e5)' }}>
                <AvisoIncompleto modalidades={modalidadesFalhas} />
              </div>
            )}

            <Filtros filtros={filtros} municipios={municipios} aoMudar={setFiltros} />

            <section className="resultado" aria-labelledby="titulo-resultado">
              <div className="resultado-topo">
                <h2 id="titulo-resultado">Licitações</h2>
                <p className="contagem" role="status">
                  {itensFiltrados.length === dados.itens.length
                    ? `${dados.itens.length} registros`
                    : `${itensFiltrados.length} de ${dados.itens.length} registros`}
                </p>
              </div>

              {itensFiltrados.length === 0 ? (
                <Vazio temFiltro={temFiltro} aoLimpar={() => setFiltros(FILTROS_INICIAIS)} />
              ) : (
                <Tabela itens={itensFiltrados} />
              )}
            </section>

            <RankingOrgaos resumo={resumo} />
          </>
        )}
      </main>

      <footer className="rodape">
        <div className="envolucro">
          <p>
            Fonte:{' '}
            <a href="https://pncp.gov.br" target="_blank" rel="noopener noreferrer">
              Portal Nacional de Contratações Públicas
            </a>
            . Os dados são recolhidos por um job diário e servidos como arquivo
            estático — por isso a página abre rápido e continua funcionando quando
            o PNCP está fora do ar.
          </p>
          <p>
            Projeto independente, sem vínculo com qualquer órgão público. Código
            aberto em{' '}
            <a
              href="https://github.com/pedrozxx/radar-licitacoes-pa"
              target="_blank"
              rel="noopener noreferrer"
            >
              github.com/pedrozxx/radar-licitacoes-pa
            </a>
            .
          </p>
        </div>
      </footer>
    </>
  )
}
