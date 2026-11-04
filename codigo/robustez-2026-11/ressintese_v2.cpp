// Teste 4 do JBCS: avalia as formulas ressintetizadas com semente fixa no protocolo v2, para um (mapa, semente).
//
// Formulas: a de marco (run_seed = 0, dados/resultados_sintese.csv, a mesma de robustez_v2) e as ressintetizadas
// com run_seed 1, 2 e 3 (analise/estatistica-2026-08/formulas_v2_seed/formulas_v2_seed.csv). Todas foram
// sintetizadas no mapa original e sao reutilizadas sem nova sintese.
// Cenarios: a mesma degradacao de robustez_v2 (protegeExtremos, degradaNiveis com a semente, 5 padroes x 3 niveis)
// e, so com a semente 42 (o original nao depende dela), o mapa original (tipo_degradacao = original, nivel 0).
// Por par valido e formula: expansoes, caminho e h(origem, destino), para a taxa de superestimacao na origem.
//
//   ./ressintese_v2 <mapa> <semente> <saida> <formulas_csv>  ->  <saida>/ressintese/<mapa>_<semente>.csv
#include "degradacao_v2.h"
#include "../medicoes-2026-08/checkpoint.h"

static vector<pair<int, string>> formulasNovas(const string &arq, const string &mapa) {
  vector<pair<int, string>> r;
  ifstream f(arq);
  string l;
  getline(f, l);
  while (getline(f, l)) {
    if (l.rfind(mapa + ",", 0) != 0) continue;
    size_t c1 = l.find(','), c2 = l.find(',', c1 + 1);
    int seed = stoi(l.substr(c1 + 1, c2 - c1 - 1));
    size_t a = l.find('"'), b = l.find('"', a + 1);
    r.push_back({seed, l.substr(a + 1, b - a - 1)});
  }
  sort(r.begin(), r.end());
  return r;
}

int main(int argc, char **argv) {
  if (argc < 5) {
    cerr << "uso: ressintese_v2 <mapa> <semente> <saida> <formulas_csv>" << endl;
    return 1;
  }
  string alvo = argv[1], saida = argv[3], arqFormulas = argv[4];
  int semente = atoi(argv[2]);
  filesystem::create_directories(saida + "/ressintese");
  string parte = saida + "/ressintese/" + alvo + "_" + to_string(semente) + ".csv";
  if (filesystem::exists(parte)) {
    cerr << "[" << alvo << " s" << semente << " ja medido, pulando]" << endl;
    return 0;
  }
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  auto formulas = formulasNovas(arqFormulas, alvo);
  if (formulas.size() != 3) {
    cerr << alvo << ": esperava 3 formulas novas em " << arqFormulas << ", achei " << formulas.size() << endl;
    return 2;
  }
  formulas.insert(formulas.begin(), {0, formulaDoMapa(alvo)});
  vector<shared_ptr<HeuristicNode>> asts;
  for (auto &[s, txt] : formulas) asts.push_back(parseFormula(txt));

  auto t0 = chrono::steady_clock::now();
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  auto original = grid;
  vector<int> tam;
  auto compOriginal = rotulaComponentes(tam);
  auto paresOriginal = paresConectados(scen);

  ofstream out(parte + ".tmp", ios::trunc);
  out << "mapa,semente,run_seed,id_problema,tipo_degradacao,porcentagem_bloqueio,exp,path,h_origem\n";
  auto avalia = [&](const vector<int> &validos, const string &tipo, double pct) {
    for (size_t f = 0; f < asts.size(); f++) {
      currentFormula = asts[f];
      for (int i : validos) {
        auto r = aStar(scen[i].start, scen[i].goal, heuristicaFormula);
        if (r.path.empty()) {
          cerr << "par valido sem caminho: id=" << i << endl;
          exit(5);
        }
        out << alvo << "," << semente << "," << formulas[f].first << "," << i << "," << tipo << "," << pct << ","
            << r.expansions << "," << (int)r.path.size() - 1 << ","
            << heuristicaFormula(scen[i].start, scen[i].goal) << "\n";
      }
    }
  };
  if (semente == 42) avalia(paresOriginal, "original", 0);
  protegeExtremos(scen);
  for (auto &p : PADROES) {
    auto v2 = degradaNiveis(p.v2, semente, true, original);
    for (size_t k = 0; k < NIVEIS.size(); k++) {
      grid = v2[k].grid;
      auto validos = verificaNivel(k ? v2[k - 1].grid : original, compOriginal, tam.size(), scen, paresOriginal,
                                   alvo + " s" + to_string(semente) + " " + p.nome);
      avalia(validos, p.nome, NIVEIS[k]);
    }
  }
  out.close();
  if (!out) {
    cerr << "falha ao gravar " << parte << endl;
    return 6;
  }
  filesystem::rename(parte + ".tmp", parte);
  cerr << "[" << alvo << " s" << semente << " pronto em "
       << chrono::duration<double>(chrono::steady_clock::now() - t0).count() << " s]" << endl;
  return 0;
}
