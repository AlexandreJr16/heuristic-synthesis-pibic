// Teste 1 do JBCS: quanto das distancias dos pivos muda com a degradacao v2, para um (mapa, semente).
//
// Mesma degradacao e mesmos pivos de robustez_v2 e complemento_v2 (srand(semente), computarDistPivos
// para 10, 20, 50 e 100, protegeExtremos, degradaNiveis). Para cada padrao, nivel e numero de pivos,
// com os pivos fixos, compara d(p, v) no mapa original com d'(p, v) no degradado:
//   mudaram            celulas livres no degradado com d'(p, v) != d(p, v) (inclui as que ficaram inalcancaveis)
//   inalcancaveis      dessas, as alcancaveis no original que ficaram com d' = -1
//   bloqueadas         celulas alcancaveis de p no original que a degradacao bloqueou (deixaram de existir)
//   u_inc              mudaram + bloqueadas: o conjunto que qualquer atualizacao incremental toca ao menos uma vez
//   u_total            celulas visitadas pelas BFS completas no degradado (o U do b3, conferido)
//   celulas_original   celulas alcancaveis dos pivos no original (soma sobre os pivos)
// Tudo somado sobre os pivos. Uma linha a mais por n (padrao = "-") registra a conferencia 4: pivos fora da
// componente do primeiro pivo no mapa original (o farthest-first esgotou a componente e sorteou fora dela).
//
//   ./incremental_v2 <mapa> <semente> <saida>   ->  <saida>/incremental/<mapa>_<semente>.csv
#include "degradacao_v2.h"

int main(int argc, char **argv) {
  if (argc < 4) {
    cerr << "uso: incremental_v2 <mapa> <semente> <saida>" << endl;
    return 1;
  }
  string alvo = argv[1], saida = argv[3];
  int semente = atoi(argv[2]);
  filesystem::create_directories(saida + "/incremental");
  string parte = saida + "/incremental/" + alvo + "_" + to_string(semente) + ".csv";
  if (filesystem::exists(parte)) {
    cerr << "[" << alvo << " s" << semente << " ja medido, pulando]" << endl;
    return 0;
  }
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  auto t0 = chrono::steady_clock::now();
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  auto original = grid;
  vector<int> tamOriginal;
  auto compOriginal = rotulaComponentes(tamOriginal);
  auto paresOriginal = paresConectados(scen);

  srand(semente);
  map<int, vector<pair<int, int>>> pivosPorN;
  map<int, vector<vector<vector<int>>>> distOriginal;
  ofstream out(parte + ".tmp", ios::trunc);
  out << "mapa,semente,padrao,nivel,n_pivos,mudaram,inalcancaveis,bloqueadas,u_inc,u_total,celulas_original,"
         "pivos_bloqueados,pivos_fora_comp_primeiro,tamanho_comp_primeiro\n";
  for (int n : NUMPIVOS) {
    computarDistPivos(n);
    pivosPorN[n] = pivos;
    distOriginal[n] = distPivos;
    auto &p0 = pivos[0];
    int c0 = compOriginal[p0.first][p0.second], fora = 0;
    for (auto &q : pivos) fora += compOriginal[q.first][q.second] != c0;
    out << alvo << "," << semente << ",-,0," << n << ",,,,,,,," << fora << "," << tamOriginal[c0] << "\n";
  }
  protegeExtremos(scen);

  for (auto &p : PADROES) {
    auto v2 = degradaNiveis(p.v2, semente, true, original);
    for (size_t k = 0; k < NIVEIS.size(); k++) {
      grid = v2[k].grid;
      verificaNivel(k ? v2[k - 1].grid : original, compOriginal, tamOriginal.size(), scen, paresOriginal,
                    alvo + " s" + to_string(semente) + " " + p.nome);
      for (int n : NUMPIVOS) {
        long long mud = 0, inal = 0, bloq = 0, tot = 0, orig = 0;
        int pb = 0;
        for (size_t j = 0; j < pivosPorN[n].size(); j++) {
          auto q = pivosPorN[n][j];
          pb += !grid[q.first][q.second];
          auto d1 = bfsPivo(q);
          auto &d0 = distOriginal[n][j];
          for (int x = 0; x < height; x++)
            for (int y = 0; y < width; y++) {
              int a = d0[x][y], b = d1[x][y];
              orig += a >= 0;
              tot += b >= 0;
              if (grid[x][y]) {
                if (a != b) {
                  mud++;
                  inal += a >= 0 && b < 0;
                }
              } else if (a >= 0 && original[x][y]) {
                bloq++;
              }
            }
        }
        out << alvo << "," << semente << "," << p.nome << "," << NIVEIS[k] << "," << n << "," << mud << "," << inal
            << "," << bloq << "," << mud + bloq << "," << tot << "," << orig << "," << pb << ",,\n";
      }
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
