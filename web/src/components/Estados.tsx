/**
 * Estados de carregamento, vazio e erro.
 *
 * Existem como componentes de verdade porque são a maior parte do tempo de uso
 * de uma ferramenta que depende de origem externa instável — e são o que a
 * maioria dos painéis trata como detalhe.
 */

/** Esqueleto com a forma das linhas que vão chegar. Círculo girando é proibido:
 *  ele não diz nada sobre o que está vindo nem quanto falta. */
export function Esqueleto({ linhas = 8 }: { linhas?: number }) {
  return (
    <div className="tabela-envolucro" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando licitações…</span>
      {Array.from({ length: linhas }, (_, i) => (
        <div
          key={i}
          style={{
            padding: 'var(--e3) var(--e4)',
            borderBottom: i < linhas - 1 ? '1px solid var(--fio)' : undefined,
            display: 'grid',
            gap: 'var(--e2)',
          }}
        >
          <div className="esqueleto-linha" style={{ width: `${58 + (i % 4) * 9}%` }} />
          <div className="esqueleto-linha" style={{ width: '34%', height: 12 }} />
        </div>
      ))}
    </div>
  )
}

/** Vazio precisa dizer POR QUE está vazio e O QUE fazer. "Nenhum resultado"
 *  sozinho faz o usuário concluir que a ferramenta está quebrada. */
export function Vazio({
  temFiltro,
  aoLimpar,
}: {
  temFiltro: boolean
  aoLimpar: () => void
}) {
  return (
    <div className="aviso">
      <h3>Nenhuma licitação encontrada</h3>
      {temFiltro ? (
        <>
          <p>
            Não há registro que atenda a todos os filtros escolhidos. Remova um
            deles ou amplie a busca.
          </p>
          <div>
            <button type="button" className="botao" onClick={aoLimpar}>
              Limpar filtros
            </button>
          </div>
        </>
      ) : (
        <p>
          O período coletado não trouxe nenhuma licitação. Isso costuma acontecer
          quando o PNCP ficou indisponível durante a coleta — a próxima execução
          diária deve corrigir.
        </p>
      )}
    </div>
  )
}

export function Erro({ mensagem, aoTentar }: { mensagem: string; aoTentar: () => void }) {
  return (
    <div className="aviso aviso--atencao" role="alert">
      <h3>Não foi possível carregar os dados</h3>
      <p>{mensagem}</p>
      <div>
        <button type="button" className="botao" onClick={aoTentar}>
          Tentar de novo
        </button>
      </div>
    </div>
  )
}

/**
 * Aviso de coleta incompleta.
 *
 * Aparece quando alguma modalidade falhou. É o oposto do corte silencioso:
 * a lista está curta e o usuário fica sabendo por quê, em vez de ler um total
 * menor como se fosse o número real.
 */
export function AvisoIncompleto({ modalidades }: { modalidades: string[] }) {
  if (modalidades.length === 0) return null
  return (
    <div className="aviso aviso--atencao" role="status">
      <h3>Esta coleta está incompleta</h3>
      <p>
        O PNCP não respondeu para {modalidades.length === 1 ? 'a modalidade' : 'as modalidades'}{' '}
        <strong>{modalidades.join(', ')}</strong> na última coleta. As licitações
        dessas modalidades não aparecem abaixo, e os totais não as incluem.
      </p>
    </div>
  )
}
