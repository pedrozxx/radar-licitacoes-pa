import {
  formatarCnpj,
  formatarData,
  formatarValor,
  textoPrazo,
} from '../lib/formatar'
import type { Licitacao } from '../lib/types'

/**
 * Tabela de resultados. Vira lista de cartões abaixo de 768px — ver
 * `global.css`. Tabela larga com rolagem horizontal em telefone esconde
 * coluna sem avisar, e aqui a coluna escondida seria o valor.
 */
export function Tabela({ itens }: { itens: Licitacao[] }) {
  return (
    <div className="tabela-envolucro">
      <table>
        <caption>
          Licitações publicadas no PNCP, da mais próxima do encerramento para a
          mais distante.
        </caption>
        <thead>
          <tr>
            <th scope="col">Objeto</th>
            <th scope="col">Município</th>
            <th scope="col">Prazo</th>
            <th scope="col" className="col-valor">
              Valor estimado
            </th>
          </tr>
        </thead>
        <tbody>
          {itens.map((item) => (
            <Linha key={item.id || `${item.orgao}-${item.publicacao}`} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Linha({ item }: { item: Licitacao }) {
  const encerrada = item.status_prazo === 'encerrado'

  return (
    <tr className={encerrada ? 'linha--encerrada' : undefined}>
      <td data-rotulo="Objeto">
        {item.link ? (
          <a
            className="objeto"
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
          >
            {item.objeto}
          </a>
        ) : (
          <span className="objeto">{item.objeto}</span>
        )}
        <span className="meta">
          {item.orgao}
          {item.cnpj && ` · ${formatarCnpj(item.cnpj)}`}
        </span>
        <span className="meta">
          {item.modalidade} · publicada em {formatarData(item.publicacao)}
        </span>
      </td>

      <td data-rotulo="Município">{item.municipio}</td>

      <td data-rotulo="Prazo">
        {/* A cor sozinha não carrega o estado: o texto sempre diz o prazo por
            extenso, e o ponto colorido só reforça o caso urgente. */}
        <span
          className={
            item.status_prazo === 'urgente' ? 'prazo prazo--urgente' : 'prazo'
          }
        >
          {item.status_prazo === 'urgente' && (
            <span className="prazo-marca" aria-hidden="true" />
          )}
          {textoPrazo(item.dias_para_encerrar)}
        </span>
        {item.encerramento && (
          <span className="meta num">{formatarData(item.encerramento)}</span>
        )}
      </td>

      <td data-rotulo="Valor estimado" className="col-valor">
        <span className={item.valor === null ? 'meta' : 'num'}>
          {formatarValor(item.valor)}
        </span>
      </td>
    </tr>
  )
}
