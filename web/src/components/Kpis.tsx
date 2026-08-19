import { formatarValorCompacto } from '../lib/formatar'
import type { Resumo } from '../lib/types'

/**
 * Fila de indicadores. São números-título, não gráficos: a resposta é um
 * valor só e um gráfico não acrescentaria nada.
 *
 * O detalhe que faz diferença é a nota sob o valor somado. O PNCP não informa
 * valor em parte dos registros, então o total cobre menos linhas do que a
 * lista mostra. Sem dizer isso, o usuário lê o número como se fosse de todos.
 */
export function Kpis({ resumo }: { resumo: Resumo }) {
  const semValor = resumo.total - resumo.com_valor

  return (
    <dl className="kpis">
      <div className="kpi">
        <dt>Licitações</dt>
        <dd className="num">{resumo.total.toLocaleString('pt-BR')}</dd>
      </div>

      <div className="kpi">
        <dt>Valor estimado</dt>
        <dd className="num">{formatarValorCompacto(resumo.valor_total)}</dd>
        <span className="kpi-nota">
          {semValor > 0
            ? `soma ${resumo.com_valor} de ${resumo.total} — o PNCP não informou valor em ${semValor}`
            : `soma as ${resumo.com_valor} licitações listadas`}
        </span>
      </div>

      <div className={resumo.urgentes > 0 ? 'kpi kpi--alerta' : 'kpi'}>
        <dt>Encerram em até 3 dias</dt>
        <dd className="num">{resumo.urgentes.toLocaleString('pt-BR')}</dd>
      </div>
    </dl>
  )
}
