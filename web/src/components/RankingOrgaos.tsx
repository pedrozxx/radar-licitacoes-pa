import { formatarValorCompacto } from '../lib/formatar'
import type { Resumo } from '../lib/types'

/**
 * Ranking de órgãos por valor somado.
 *
 * Barras horizontais porque o dado é magnitude comparada entre categorias com
 * nome longo — nome de órgão não cabe embaixo de barra vertical sem virar
 * texto na diagonal.
 *
 * **Uma cor só.** É série única: cada barra é o mesmo tipo de coisa, e pintar
 * cada órgão de um tom diferente sugeriria uma identidade que não existe. Cor
 * por posição no ranking também seria errada — bastaria filtrar para repintar
 * tudo e o leitor perderia a referência.
 *
 * Sem legenda de propósito: com série única, o título já diz o que é.
 */
export function RankingOrgaos({ resumo }: { resumo: Resumo }) {
  if (resumo.por_orgao.length === 0) return null

  const maior = resumo.por_orgao[0]?.valor ?? 0
  if (maior <= 0) return null

  return (
    <section className="ranking" aria-labelledby="titulo-ranking">
      <h2 id="titulo-ranking">Órgãos que mais compram</h2>
      <p className="ranking-legenda">
        Soma do valor estimado das licitações listadas, por órgão.
      </p>

      <ol className="ranking-lista">
        {resumo.por_orgao.map((linha) => {
          const proporcao = Math.max((linha.valor / maior) * 100, 1)
          return (
            <li className="ranking-item" key={linha.orgao}>
              <span className="ranking-nome" title={linha.orgao}>
                {linha.orgao}
              </span>
              <span className="ranking-valor num">
                {formatarValorCompacto(linha.valor)}
              </span>
              {/* A barra é decoração do número que já está escrito ao lado,
                  então fica fora da árvore de acessibilidade — o leitor de
                  tela ouve nome e valor, sem "imagem" no meio. */}
              <div className="ranking-barra" aria-hidden="true">
                <div
                  className="ranking-preenchimento"
                  style={{ width: `${proporcao}%` }}
                />
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
