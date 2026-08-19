import { FILTROS_INICIAIS, type Filtros as TipoFiltros } from '../lib/types'

interface Props {
  filtros: TipoFiltros
  municipios: string[]
  aoMudar: (filtros: TipoFiltros) => void
}

const ROTULOS_STATUS: Record<TipoFiltros['status'], string> = {
  todas: 'todas',
  abertas: 'só abertas',
  urgentes: 'só urgentes',
}

/**
 * Painel de filtros.
 *
 * Cada filtro ativo vira um marcador removível abaixo dos campos. Sem isso o
 * usuário rola até a lista, vê poucos resultados e não lembra que ele mesmo
 * restringiu a busca — e conclui que faltam dados.
 */
export function Filtros({ filtros, municipios, aoMudar }: Props) {
  const ativos: { chave: keyof TipoFiltros; texto: string }[] = []
  if (filtros.municipio) ativos.push({ chave: 'municipio', texto: filtros.municipio })
  if (filtros.busca.trim()) ativos.push({ chave: 'busca', texto: `"${filtros.busca}"` })
  if (filtros.status !== 'todas')
    ativos.push({ chave: 'status', texto: ROTULOS_STATUS[filtros.status] })

  function limpar(chave: keyof TipoFiltros) {
    aoMudar({ ...filtros, [chave]: FILTROS_INICIAIS[chave] })
  }

  return (
    <section aria-labelledby="titulo-filtros">
      <h2 id="titulo-filtros" className="sr-only">
        Filtros
      </h2>

      <div className="filtros">
        <div className="campo">
          <label htmlFor="busca">Buscar no objeto ou órgão</label>
          <input
            id="busca"
            type="search"
            value={filtros.busca}
            placeholder="papel, ambulância, obra..."
            onChange={(e) => aoMudar({ ...filtros, busca: e.target.value })}
          />
        </div>

        <div className="campo">
          <label htmlFor="municipio">Município</label>
          <select
            id="municipio"
            value={filtros.municipio}
            onChange={(e) => aoMudar({ ...filtros, municipio: e.target.value })}
          >
            <option value="">Todos ({municipios.length})</option>
            {municipios.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="campo">
          <label htmlFor="status">Situação do prazo</label>
          <select
            id="status"
            value={filtros.status}
            onChange={(e) =>
              aoMudar({ ...filtros, status: e.target.value as TipoFiltros['status'] })
            }
          >
            <option value="todas">Todas</option>
            <option value="abertas">Com proposta aberta</option>
            <option value="urgentes">Encerram em até 3 dias</option>
          </select>
        </div>

        <div className="campo">
          <label htmlFor="ordenar">Ordenar por</label>
          <select
            id="ordenar"
            value={filtros.ordenar}
            onChange={(e) =>
              aoMudar({ ...filtros, ordenar: e.target.value as TipoFiltros['ordenar'] })
            }
          >
            <option value="prazo">Prazo mais próximo</option>
            <option value="valor">Maior valor</option>
            <option value="publicacao">Publicação mais recente</option>
          </select>
        </div>
      </div>

      <div className="marcadores">
        {ativos.length > 0 && (
          <>
            <span className="contagem">Filtrando por:</span>
            {ativos.map((a) => (
              <span className="marcador" key={a.chave}>
                {a.texto}
                <button
                  type="button"
                  onClick={() => limpar(a.chave)}
                  aria-label={`Remover filtro ${a.texto}`}
                >
                  ×
                </button>
              </span>
            ))}
            <button
              type="button"
              className="botao botao--fantasma"
              onClick={() => aoMudar(FILTROS_INICIAIS)}
            >
              limpar tudo
            </button>
          </>
        )}
      </div>
    </section>
  )
}
