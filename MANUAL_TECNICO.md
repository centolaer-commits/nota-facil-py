# Documentação Técnica e Guia de Repasse - NubePY

## 1. Visão Geral do Sistema

O **NubePY** é um sistema web de gestão (ERP) e Ponto de Venda (PDV) projetado especificamente para o mercado paraguaio. O sistema opera como um SaaS (Software as a Service) e tem como principal diferencial a integração nativa com a API do **SIFEN** (Sistema Integrado de Facturación Electrónica Nacional) para emissão de Facturas Electrónicas.

### Tecnologias Utilizadas (Stack)

| Camada | Tecnologia |
|---|---|
| **Frontend** | HTML5, CSS3 (Tailwind CSS via CDN) e JavaScript puro (Vanilla JS). Arquitetura em modelo Single Page Application (SPA). |
| **Backend** | Python com **FastAPI** (framework assíncrono moderno) |
| **Banco de Dados** | **PostgreSQL** via biblioteca `psycopg2` |
| **Hospedagem / Servidor** | **Render.com** (Web Service + PostgreSQL gerenciado) |
| **Controle de Versão** | Git / GitHub (branch `main` com deploy automático) |

### Dependências Principais (requirements.txt)

```
fastapi              # Framework web
uvicorn              # Servidor ASGI
pydantic             # Validação de dados
qrcode               # Geração de QR Code (KUDE)
reportlab / fpdf     # Geração de PDF (Facturas)
psycopg2-binary      # Conexão PostgreSQL
cryptography         # Manipulação de certificados digitais
signxml              # Assinatura XMLDSig (exigência SIFEN)
lxml                 # Parse XML
zeep                 # Cliente SOAP (comunicação SIFEN)
requests             # HTTP client
mercadopago==2.3.0   # Pagamentos PIX via Mercado Pago
python-multipart     # Upload de arquivos (certificados)
```

---

## 2. Estrutura do Frontend

O frontend foi construído para ser rápido e leve, operando principalmente em dois arquivos centrais:

- **`frontend.html`**: Contém toda a estrutura visual do sistema. As telas (Dashboard, Inventário, PDV, Configurações, Cierre de Caja, etc.) estão separadas por `<div>` com IDs específicos (ex: `#tela-dashboard`, `#tela-pos`, `#tela-inventario`). A navegação ocorre ocultando e exibindo esses containers via CSS (`classList.remove('hidden')` / `style.display = 'block'|'none'`), garantindo transições instantâneas sem recarregar a página.

- **`app.js`**: Gerencia toda a lógica do lado do cliente. Responsável por:
  - **Autenticação e Sessão**: Envio de credenciais para `/api/login`, armazenamento do `empresa_id` e `rol` no `sessionStorage`.
  - **Navegação (`mudarTela`)**: Função que alterna entre as 16 telas do sistema via ID.
  - **Comunicação com a API**: Realiza fetch para o backend FastAPI em Python para CRUD de produtos, fornecedores, clientes, envio de notas ao SIFEN, geração de PDF, etc.
  - **Leitor de Código de Barras**: Suporte a câmera do celular (QuaggaJS / câmera nativa) para captura de códigos.

### Estrutura de Telas (IDs)

| ID | Tela |
|---|---|
| `#tela-dashboard` | Dashboard principal |
| `#tela-pos` | Ponto de Venda (PDV) |
| `#tela-inventario` | Inventário / Produtos |
| `#tela-proveedores` | Fornecedores |
| `#tela-notas` | Facturas Electrónicas emitidas |
| `#tela-autofactura` | Autofacturas (vendedores informais) |
| `#tela-remision` | Remissões / Guias de remessa |
| `#tela-entrada` | Entrada de mercadorias / Gastos operacionais |
| `#tela-mermas` | Perdas / Mermas de estoque |
| `#tela-config` | Configurações da empresa |
| `#tela-equipo` | Gestão de funcionários / equipa |
| `#tela-cierre` | Cierre de Caixa (fechamento diário) |
| `#tela-sangria` | Sangrias de caixa |
| `#tela-categorias` | Categorias de produtos |
| `#tela-auditoria` | Auditoria de inventário |
| `#tela-admin` | Super Admin (gestão de múltiplas empresas) |

### Controle de Versão do Frontend

O arquivo `app.js` possui um sistema de versionamento via parâmetro `?v=N` na URL para quebra de cache do navegador. A versão atual é `v=28`. Para forçar a atualização no navegador do cliente: **Ctrl+F5**.

---

## 3. Estrutura do Backend (FastAPI)

### Arquivos do Projeto

```
nota-facil-py/
├── main.py                  # Servidor FastAPI (rotas da API, ~1100 linhas)
├── banco_dados.py           # Camada de dados PostgreSQL (conexão, queries, migrações)
├── gerador_xml.py           # Montagem do XML da Factura Electrónica (formato SIFEN)
├── assinador_xml.py         # Assinatura digital XMLDSig (certificado .p12)
├── conexao_sifen.py         # Envio SOAP para servidores da SET
├── gerador_kude.py          # Geração de QR Code KUDE (Código Único de Documento Electrónico)
├── gerador_pdf.py           # Geração do PDF da Factura (fpdf)
├── transmissor_sifen.py     # Transmissão batch para SIFEN
├── validador_local_sifen.py # Validador estrutural offline (XML vs XSD)
├── frontend.html            # Interface SPA do sistema
├── app.js                   # Lógica frontend
└── requirements.txt         # Dependências Python
```

### Endpoints da API (principais)

#### Autenticação e Empresa
| Método | Rota | Função |
|---|---|---|
| `POST` | `/api/login` | Autenticação por RUC + senha (admin ou caixa) ou email + hash (funcionários) |
| `POST` | `/validar-admin` | Validação de senha admin para operações sensíveis |
| `GET` | `/dados-dashboard` | Métricas do dashboard (faturamento do dia, produtos mais vendidos) |
| `GET` | `/status-caixa` | Status do caixa (aberto/fechado) |
| `POST` | `/abrir-caixa` | Abertura de caixa (valor inicial) |
| `POST` | `/fechar-caixa` | Fechamento de caixa (valor final) |
| `POST` | `/registrar-sangria` | Registro de sangria |

#### Produtos e Inventário
| Método | Rota | Função |
|---|---|---|
| `POST` | `/cadastrar-produto` | Cadastro de novo produto |
| `GET` | `/listar-produtos` | Lista todos os produtos |
| `GET` | `/buscar-produto/{codigo_barras}` | Busca produto por código de barras |
| `DELETE` | `/deletar-produto/{codigo_barras}` | Remove produto |
| `POST` | `/cadastrar-categoria` | Nova categoria |
| `GET` | `/listar-categorias` | Lista categorias |
| `POST` | `/cadastrar-proveedor` | Novo fornecedor |
| `GET` | `/listar-proveedores` | Lista fornecedores |

#### Facturação Electrónica (SIFEN)
| Método | Rota | Função |
|---|---|---|
| `POST` | `/emitir-nota` | Emissão de Factura Electrónica (completa: XML → assinatura → SIFEN → PDF → QR) |
| `POST` | `/emitir-remision` | Emissão de Remissão / Guia de remessa |
| `POST` | `/emitir-autofactura` | Emissão de Autofactura (vendedores sem RUC) |
| `GET` | `/listar-notas` | Lista facturas emitidas (com filtro por data/busca) |
| `GET` | `/api/nota/{cdc}` | Detalhes de uma nota pelo CDC |
| `GET` | `/baixar-pdf/{id_nota}` | Download do PDF da factura |
| `POST` | `/upload-certificado` | Upload do certificado digital .p12 |
| `POST` | `/alternar-ambiente` | Alterna entre ambiente testes/produção |
| `GET` | `/obter-configuracao` | Obtém configurações da empresa |
| `POST` | `/salvar-configuracao` | Salva configurações |

#### Pagamentos
| Método | Rota | Função |
|---|---|---|
| `POST` | `/gerar-pix` | Gera QR Code PIX via Mercado Pago (conversão PYG → BRL) |
| `GET` | `/status-pix/{pagamento_id}` | Consulta status do pagamento PIX |

#### Super Admin
| Método | Rota | Função |
|---|---|---|
| `GET` | `/super-admin/empresas` | Lista todas as empresas registadas |
| `GET` | `/super-admin/metricas` | Métricas globais do SaaS |
| `POST` | `/super-admin/criar-empresa` | Cria nova empresa no sistema |
| `PUT` | `/super-admin/editar-empresa/{id}` | Edita plano/valor de empresa |

---

## 4. Autenticação e Segurança

### Sistema de Login

O NubePY utiliza **autenticação por comparação direta** (não utiliza JWT ou tokens de sessão):

1. **Admin / Dono**: Login com RUC + senha em texto plano (armazenada na coluna `senha_admin` da tabela `empresas`)
2. **Caixa (legado)**: Login com RUC + senha em texto plano (coluna `senha_caixa`)
3. **Funcionários**: Login por email + senha com hash SHA256 (coluna `senha_hash` da tabela `funcionarios`)
4. **Super Admin**: Login com RUC especial `NUBE`

### Identificação por Cabeçalho

Após autenticação, a empresa é identificada em cada requisição via cabeçalho HTTP:
```
X-Empresa-ID: <id_da_empresa>
```

Não há `SECRET_KEY` ou variável de ambiente para JWT — a segurança é baseada na validação de senha a cada requisição e no uso de HTTPS (gerido pelo Render).

### Senha Padrão de Fábrica

- **Admin**: `admin123` (alterável na tela de Configurações)
- **Caixa**: `caja123` (alterável pelo admin)

---

## 5. Integração SIFEN (O Núcleo do Sistema)

Este é o módulo de maior valor da plataforma. O backend em Python é responsável por:

### Fluxo Completo de Emissão

```
Frontend (PDV) → FastAPI → gerador_xml.py → assinador_xml.py → conexao_sifen.py (SOAP) → SIFEN/SET
                                                                                            ↓
                                                                                    KUDE (CDC) ←
                                                                                            ↓
                                                                         gerador_pdf.py + gerador_kude.py
                                                                                            ↓
                                                                         PDF + QR Code → Frontend
```

### 1. Montagem do XML (`gerador_xml.py`)
Recebe os dados da venda do frontend e estrutura no formato XML oficial do SIFEN (Manual Técnico v150). Inclui:
- Dados do emitente (RUC, nome, endereço)
- Dados do cliente (nome, RUC opcional)
- Itens da venda (descrição, quantidade, preço unitário)
- Cálculo do CDC (Código de Control de Documento) com algoritmo módulo 11
- Cálculo do dígito verificador do RUC

### 2. Assinatura Digital (`assinador_xml.py`)
Aplica a assinatura **XMLDSig Enveloped (RSA-SHA256)** exigida pela SIFEN:
- Carrega o certificado digital da empresa no formato **PKCS#12 (.p12)**
- Usa a biblioteca `signxml` para aplicar a assinatura
- O certificado é armazenado na pasta `certificados/` e referenciado por empresa

### 3. Transmissão para a SET (`conexao_sifen.py`)
Envia o pacote via **SOAP (WSDL)** com **mTLS** (mutual TLS usando o certificado digital):
- **Ambiente de Testes**: `https://sifen-test.set.gov.py/de/ws/sync/recepcion.wsdl`
- **Produção**: `https://sifen.set.gov.py/de/ws/sync/recepcion.wsdl`
- Método SOAP: `rEnviDe` (Recepción Síncrona de 1 Documento)
- Retorna: `dCodRes` (código de retorno) + `dMsgRes` (mensagem)

### 4. Geração do KUDE e QR Code (`gerador_kude.py`)
Após aprovação, gera:
- **CDC** (Código de Control): 44 dígitos alfanuméricos que identificam unicamente a factura
- **QR Code** com URL de consulta no portal da SET: `https://ekuatia.set.gov.py/consultas/qr?nId={cdc_id}`

### 5. Geração do PDF (`gerador_pdf.py`)
Gera o PDF da Factura Electrónica com biblioteca `fpdf`, incluindo:
- Cabeçalho com dados da empresa
- Tabela de itens
- QR Code impresso
- CDC e dados de validação

### Modo Demo / Sandbox

O sistema inclui um **escudo de segurança** que impede que usuários demo enviem dados reais para a SET:
```python
if ruc_emissor == "9999999-9":
    # Simula resposta de sucesso sem enviar para a SET
```

Isso permite que clientes testem todo o fluxo sem risco de enviar dados inválidos para o governo.

### Importante para Novo Proprietário
- Para ativar a **emissão real** de notas para um novo cliente, é necessário:
  1. Inserir o **certificado digital (.p12)** válido do cliente na tela de Configurações
  2. Configurar o **CSC** (Código de Seguridad del Contribuyente) fornecido pela SET
  3. Alternar o ambiente de **Testes → Produção**

---

## 6. Banco de Dados (PostgreSQL)

### Estrutura

A conexão é feita via variável de ambiente `DATABASE_URL`:
```python
DATABASE_URL = os.environ.get("DATABASE_URL")
```

### Tabelas Principais

| Tabela | Finalidade |
|---|---|
| `empresas` | Dados cadastrais, plano, certificado, credenciais, configuração SIFEN |
| `funcionarios` | Utilizadores do sistema (caixas, gerentes) com autenticação SHA256 |
| `produtos` | Catálogo de produtos (código de barras, descrição, preço, stock) |
| `proveedores` | Fornecedores |
| `categorias` | Categorias de produtos |
| `notas` | Histórico de facturas electrónicas emitidas |
| `caixa_movimentos` | Movimentações de caixa (abertura, fechamento, sangrias) |
| `entradas_mercadoria` | Entradas de stock com custo |
| `autofacturas` | Autofacturas emitidas |
| `remisiones` | Guias de remessa |
| `mermas` | Perdas de inventário |
| `auditorias` / `auditoria_itens` | Contagem física de inventário |
| `faturas_saas` | Faturas de cobrança SaaS (geradas pelo Super Admin) |

### Colunas Específicas da Tabela `empresas`

| Coluna | Descrição |
|---|---|
| `ruc` | RUC da empresa (identificador único) |
| `senha_admin` | Senha do administrador (texto plano - legado) |
| `senha_caixa` | Senha do caixa (texto plano - legado) |
| `ambiente_sifen` | `testes` ou `produccion` |
| `caminho_certificado` | Caminho do arquivo .p12 no servidor |
| `senha_certificado` | Senha do certificado digital |
| `csc` | Código de Seguridad del Contribuyente (SIFEN) |
| `mercado_pago_token` | Token de integração Mercado Pago (PIX) |
| `plano` | Plano de assinatura (Inicial, Premium, VIP, Demo, etc.) |
| `status_assinatura` | Activo / Inactivo |

---

## 7. Integração Mercado Pago (PIX)

O sistema permite que clientes paguem via **PIX** através do Mercado Pago.

**Fluxo:**
1. Frontend solicita geração de PIX com valor em **Guaranis (PYG)**
2. Backend consulta taxa de câmbio atual BRL↔PYG via AwesomeAPI (`https://economia.awesomeapi.com.br/last/BRL-PYG`)
3. Converte PYG → BRL
4. Comunica com SDK do Mercado Pago para gerar QR Code PIX
5. Retorna o QR Code e ID do pagamento ao frontend
6. Frontend consulta `/status-pix/{id}` até confirmação

---

## 8. Ambiente de Hospedagem (Render)

### Deploy

O sistema está hospedado na plataforma **Render.com** como **Web Service**. O deploy é automatizado via Git:

1. Código enviado para branch `main` do repositório GitHub `nota-facil-py`
2. Render detecta o push e inicia build automático
3. Web Service reinicia com a nova versão

### Configuração do Web Service (Render)

| Configuração | Valor |
|---|---|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/` |

### Variáveis de Ambiente (Render)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | ✅ Sim | String de conexão PostgreSQL fornecida pelo Render |
| `PYTHON_VERSION` | Recomendado | Versão do Python (ex: `3.11.0`) |

**Nota:** As URLs do SIFEN estão **hardcoded** no código (`conexao_sifen.py`), não sendo necessária variável de ambiente para tal. O sistema também **não utiliza JWT** nem `SECRET_KEY` externa — a autenticação é baseada em comparação de senhas armazenadas no banco.

### Acesso ao Servidor

- **URL do sistema**: `https://nubepy.onrender.com` (a definir com domínio próprio)
- **Painel Render**: `https://dashboard.render.com` (acesso ao Web Service e PostgreSQL)
- **Repositório GitHub**: `https://github.com/enricocentola/nota-facil-py`

---

## 9. Ambiente de Sandbox / Demonstração

O sistema inclui um modo **demo público** acessível via rota `/demo`:

- **Login automático** com RUC `9999999-9` e senha `demo123`
- **Dados de demonstração** injetados automaticamente (produtos, fornecedores, categorias)
- **Sessão expira** em 1 hora (com limite de 10 transações)
- **Facturas demo** são simuladas (nunca enviadas para a SET real)
- **Auto-limpeza** de sessões expiradas ao iniciar o servidor

---

## 10. Planos de Assinatura (SaaS)

| Plano | Descrição | SIFEN | Funcionários |
|---|---|---|---|
| **Lite** | Sistema básico sem facturação fiscal | ❌ | 1 usuário (dono) |
| **Lite Premium** | Lite com relatórios avançados | ❌ | 1 usuário |
| **Demo** | Teste gratuito (limitado) | ✅ (simulado) | 1 usuário |
| **Inicial** | Facturação fiscal inclusa | ✅ | 1 usuário (dono) |
| **Premium** | Equipa completa | ✅ | Até 5 funcionários |
| **VIP** | Completo + suporte prioritário | ✅ | Ilimitado |
| **Crecimiento** | Plano de crescimento | ✅ | Até 3 funcionários |

---

## 11. Suporte a Múltiplas Empresas (Super Admin)

O sistema é **multi-empresa** (SaaS). O Super Admin pode:
- Listar todas as empresas registadas (`/super-admin/empresas`)
- Criar novas empresas (`/super-admin/criar-empresa`)
- Editar planos e valores (`/super-admin/editar-empresa/{id}`)
- Emitir faturas de cobrança (`/super-admin/gerar-fatura/{id}`)
- Visualizar métricas globais (`/super-admin/metricas`)

Acesso Super Admin: login com RUC `NUBE` + senha admin.

---

## 12. Checklist de Transferência de Propriedade

Para concluir a transição, os seguintes ativos digitais serão transferidos para o e-mail do comprador:

| Item | Detalhes |
|---|---|
| [ ] **Domínio** | Transferência do domínio **nubepy.com** (via provedor de registro — atualmente Cloudflare ou similar) |
| [ ] **Repositório de Código** | Transferência da propriedade do repositório `nota-facil-py` no GitHub (conta: `enricocentola`) |
| [ ] **Hospedagem** | Transferência do Web Service e Banco de Dados PostgreSQL no painel do Render.com (dashboard.render.com) |
| [ ] **Mercado Pago** | Credenciais e tokens de acesso da conta Mercado Pago utilizada para PIX |
| [ ] **Redes Sociais** | Senhas e acessos de administrador para Instagram, Facebook, LinkedIn (contas @nubepy ou a definir) |
| [ ] **E-mail Corporativo** | Acesso à conta de e-mail principal (`contato@nubepy.com`) |
| [ ] **WhatsApp Business** | Número `+595 986 347 328` (conta WhatsApp Business vinculada ao sistema de notificações) |
| [ ] **Certificados Digitais** | Certificados .p12 dos clientes activos (armazenados na pasta `certificados/` do servidor) |

---

## 13. Suporte e Contactos

- **Desenvolvedor Original**: Enrico Centola
- **E-mail**: (a definir / transferir para o novo proprietário)
- **WhatsApp**: +595 986 347 328
- **Stack técnica**: Python (FastAPI) + PostgreSQL + Render + GitHub
- **Última actualização deste manual**: Maio de 2026

---

*Documento gerado automaticamente por Pyra 🐍⚡ com base em varredura completa do código-fonte e configurações do sistema NubePY.*
