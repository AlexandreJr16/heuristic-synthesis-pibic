#include "degradacao_v2.h"

bool aplicaRegras = true;
long long rejeitadasR1 = 0, rejeitadasR2 = 0, tentativasR1 = 0, tentativasR2 = 0, chamadasBfs = 0, celulasBfs = 0;

static vector<char> protegida, recusada;
static vector<int> marca;
static int geracao = 0;

// Anel 3x3 em ordem ciclica (N, NE, L, SE, S, SO, O, NO): vizinhos consecutivos sao 4-adjacentes
static const int anelX[8] = {-1, -1, 0, 1, 1, 1, 0, -1};
static const int anelY[8] = {0, 1, 1, 1, 0, -1, -1, -1};

const vector<double> NIVEIS = {0.1, 0.2, 0.3};

static bool livre(int x, int y) { return x >= 0 && x < height && y >= 0 && y < width && grid[x][y]; }

void protegeExtremos(const vector<ScenProblem> &scen) {
  protegida.assign(height * width, 0);
  marca.assign(height * width, 0);
  geracao = 0;
  for (auto &p : scen) {
    protegida[p.start.first * width + p.start.second] = 1;
    protegida[p.goal.first * width + p.goal.second] = 1;
  }
}

// Um vizinho ortogonal livre por trecho contiguo de celulas livres do anel 3x3.
// Os trechos sao as componentes locais: um trecho so = bloquear nao desconecta
static vector<pair<int, int>> trechosLocais(int x, int y) {
  bool f[8];
  for (int k = 0; k < 8; k++) f[k] = livre(x + anelX[k], y + anelY[k]);
  int inicio = 0;
  while (inicio < 8 && f[inicio]) inicio++;
  if (inicio == 8) return {{x + anelX[0], y + anelY[0]}};
  vector<pair<int, int>> reps;
  bool temRep = false;
  for (int d = 1; d <= 8; d++) {
    int k = (inicio + d) % 8;
    if (!f[k]) {
      temRep = false;
      continue;
    }
    if (k % 2 == 0 && !temRep) {
      reps.push_back({x + anelX[k], y + anelY[k]});
      temRep = true;
    }
  }
  return reps;
}

// BFS bidirecional com parada antecipada: as frentes avancam alternadamente; encontro = ligados,
// fila vazia = aquele lado ficou fechado
static bool ligados(pair<int, int> a, pair<int, int> b) {
  static vector<int> fila[2];
  chamadasBfs++;
  geracao++;
  int marcaLado[2] = {2 * geracao, 2 * geracao + 1};
  int ia = a.first * width + a.second, ib = b.first * width + b.second;
  if (ia == ib) return true;
  size_t cab[2] = {0, 0};
  fila[0].assign(1, ia);
  fila[1].assign(1, ib);
  marca[ia] = marcaLado[0];
  marca[ib] = marcaLado[1];
  for (int lado = 0;; lado ^= 1) {
    if (cab[lado] == fila[lado].size()) return false;
    int v = fila[lado][cab[lado]++];
    celulasBfs++;
    int vx = v / width, vy = v % width;
    for (int k = 0; k < 4; k++) {
      int nx = vx + px[k], ny = vy + py[k];
      if (!livre(nx, ny)) continue;
      int u = nx * width + ny;
      if (marca[u] == marcaLado[lado ^ 1]) return true;
      if (marca[u] == marcaLado[lado]) continue;
      marca[u] = marcaLado[lado];
      fila[lado].push_back(u);
    }
  }
}

bool bloqueia(int x, int y) {
  if (!aplicaRegras) {
    grid[x][y] = false;
    return true;
  }
  int i = x * width + y;
  if (protegida[i]) {
    tentativasR1++;
    rejeitadasR1 += !recusada[i];
    recusada[i] = 1;
    return false;
  }
  auto reps = trechosLocais(x, y);
  grid[x][y] = false;
  for (size_t j = 1; j < reps.size(); j++)
    if (!ligados(reps[0], reps[j])) {
      grid[x][y] = true;
      tentativasR2++;
      rejeitadasR2 += !recusada[i];
      recusada[i] = 1;
      return false;
    }
  return true;
}

bool celulaRecusada(int x, int y) { return recusada[x * width + y]; }

// Os cinco mecanismos abaixo sao os de map.cpp, linha a linha; so o ponto de bloqueio passa por bloqueia()

static int radialV2(int raio, double aspecto) {
  int xa = rand() % height;
  int ya = rand() % width;
  int blocked = 0;
  if (grid[xa][ya])
    for (int y = -raio; y <= raio; y++)
      for (int x = -raio * aspecto; x <= raio * aspecto; x++) {
        int ix = x + xa;
        int iy = y + ya;
        float dist = sqrt(pow(x / aspecto, 2) + pow(y, 2));
        if (dist <= raio && ix >= 0 && iy >= 0 && ix < height && iy < width && grid[ix][iy] && bloqueia(ix, iy))
          blocked++;
      }
  return blocked;
}

static void degradaRadialV2(int targetBlocked) {
  int currentBlocked = 0;
  int tries = 0;
  int raio = max(2, min(height, width) / 20);
  while (currentBlocked < targetBlocked && tries < height * width) {
    currentBlocked += radialV2(raio, 1.0);
    tries++;
  }
}

static int linearV2(int length) {
  int xa = rand() % height;
  int ya = rand() % width;
  int blocked = 0;
  if (grid[xa][ya]) {
    int dir = rand() % 4;
    int currX = xa;
    int currY = ya;
    for (int i = 0; i < length; i++) {
      if (currX >= 0 && currX < height && currY >= 0 && currY < width && grid[currX][currY] &&
          bloqueia(currX, currY))
        blocked++;
      currX += px[dir];
      currY += py[dir];
    }
  }
  return blocked;
}

static void degradaLinearV2(int targetBlocked) {
  int currentBlocked = 0;
  int tries = 0;
  int length = max(10, min(height, width) / 2);
  while (currentBlocked < targetBlocked && tries < height * width) {
    currentBlocked += linearV2(length);
    tries++;
  }
}

static int sparseV2(int raio, double density) {
  int xa = rand() % height;
  int ya = rand() % width;
  int blocked = 0;
  if (grid[xa][ya])
    for (int y = -raio; y <= raio; y++)
      for (int x = -raio; x <= raio; x++) {
        int ix = xa + x;
        int iy = ya + y;
        float dist = sqrt(x * x + y * y);
        if (dist <= raio && ix >= 0 && iy >= 0 && ix < height && iy < width) {
          double chance = (rand() % 1000) / 1000.0;
          if (chance < density && grid[ix][iy] && bloqueia(ix, iy)) blocked++;
        }
      }
  return blocked;
}

static void degradaSparseV2(int targetBlocked) {
  int currentBlocked = 0;
  int tries = 0;
  int raio = max(5, min(height, width) / 10);
  while (currentBlocked < targetBlocked && tries < height * width) {
    currentBlocked += sparseV2(raio, 0.4);
    tries++;
  }
}

static int organicV2(int numCells) {
  int xa = rand() % height;
  int ya = rand() % width;
  int blocked = 0;
  if (grid[xa][ya]) {
    int currX = xa;
    int currY = ya;
    int maxIterations = numCells * 5;
    for (int i = 0; i < maxIterations && blocked < numCells; i++) {
      if (currX >= 0 && currX < height && currY >= 0 && currY < width && grid[currX][currY] &&
          bloqueia(currX, currY))
        blocked++;
      int dir = rand() % 4;
      currX += px[dir];
      currY += py[dir];
      if (currX < 0 || currX >= height || currY < 0 || currY >= width) {
        currX = xa;
        currY = ya;
      }
    }
  }
  return blocked;
}

static void degradaOrganicV2(int targetBlocked) {
  int currentBlocked = 0;
  int tries = 0;
  int numCells = max(20, (height * width) / 250);
  while (currentBlocked < targetBlocked && tries < height * width) {
    currentBlocked += organicV2(numCells);
    tries++;
  }
}

static void degradaSaundersV2(int targetBlocked) {
  int currentBlocked = 0;
  int tries = 0;
  while (currentBlocked < targetBlocked && tries < height * width * 10) {
    int x = rand() % height;
    int y = rand() % width;
    if (grid[x][y] && bloqueia(x, y)) currentBlocked++;
    tries++;
  }
}

const vector<Padrao> PADROES = {{"Radial", degradaMapa, degradaRadialV2},
                                {"Linear", degradaMapaLinear, degradaLinearV2},
                                {"Sparse", degradaMapaSparse, degradaSparseV2},
                                {"Organic", degradaMapaOrganic, degradaOrganicV2},
                                {"Stochastic", degradaMapaSaunders, degradaSaundersV2}};

static int bloqueadasAgora() {
  int livres = 0;
  for (int i = 0; i < height; i++)
    for (int j = 0; j < width; j++) livres += grid[i][j];
  return originalTraversableCells - livres;
}

// metaAbsoluta = false repete main.cpp:209-215 (incremento entre alvos);
// true pede ao gerador so o que falta para o alvo do nivel (R3)
vector<Nivel> degradaNiveis(void (*degrada)(int), int semente, bool metaAbsoluta,
                            const vector<vector<bool>> &original) {
  grid = original;
  srand(semente);
  rejeitadasR1 = rejeitadasR2 = tentativasR1 = tentativasR2 = 0;
  recusada.assign(height * width, 0);
  vector<Nivel> niveis;
  int lastTarget = 0;
  for (double pct : NIVEIS) {
    int target = static_cast<int>(originalTraversableCells * pct);
    degrada(target - (metaAbsoluta ? bloqueadasAgora() : lastTarget));
    niveis.push_back({grid, (double)bloqueadasAgora() / originalTraversableCells, rejeitadasR1, rejeitadasR2,
                      tentativasR1, tentativasR2});
    lastTarget = target;
  }
  return niveis;
}

uint64_t hashGrid() {
  uint64_t h = 1469598103934665603ULL;
  for (int i = 0; i < height; i++)
    for (int j = 0; j < width; j++) h = (h ^ grid[i][j]) * 1099511628211ULL;
  return h;
}

vector<int> paresConectados(const vector<ScenProblem> &scen) {
  vector<int> tam;
  auto comp = rotulaComponentes(tam);
  vector<int> pares;
  for (size_t i = 0; i < scen.size(); i++) {
    int a = comp[scen[i].start.first][scen[i].start.second];
    if (a != -1 && a == comp[scen[i].goal.first][scen[i].goal.second]) pares.push_back(i);
  }
  return pares;
}

static void falha(const string &contexto, const string &regra) {
  cerr << "VERIFICACAO FALHOU [" << contexto << "]: " << regra << endl;
  exit(5);
}

vector<int> verificaNivel(const vector<vector<bool>> &anterior, const vector<vector<int>> &compOriginal,
                          int nCompOriginal, const vector<ScenProblem> &scen,
                          const vector<int> &paresOriginal, const string &contexto) {
  for (auto &p : scen)
    if (!grid[p.start.first][p.start.second] || !grid[p.goal.first][p.goal.second])
      falha(contexto, "R1 (extremo de par bloqueado)");
  for (int i = 0; i < height; i++)
    for (int j = 0; j < width; j++)
      if (grid[i][j] && !anterior[i][j]) falha(contexto, "cumulatividade (celula desbloqueada)");
  vector<int> tam;
  auto comp = rotulaComponentes(tam);
  if ((int)tam.size() > nCompOriginal) falha(contexto, "R2 (numero de componentes aumentou)");
  vector<int> novaDe(nCompOriginal, -1);
  for (int i = 0; i < height; i++)
    for (int j = 0; j < width; j++) {
      if (comp[i][j] == -1) continue;
      int &n = novaDe[compOriginal[i][j]];
      if (n == -1) n = comp[i][j];
      if (n != comp[i][j]) falha(contexto, "R2 (componente original dividida)");
    }
  auto pares = paresConectados(scen);
  if (pares != paresOriginal) falha(contexto, "par conectado no original ficou desconectado");
  return pares;
}
