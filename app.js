let empresaAtualId = null; let rolUsuario = null; let planoAtivo = ''; let rucAtual = null; let funcionarioId = null; let nomeFuncionario = ''; let productosGlobais = [];

// Constantes de perfis RBAC
const PERFIL_OWNER = 'admin';
const PERFIL_MANAGER = 'manager';
const PERFIL_CASHIER = 'cajero'; let productosCaixa = []; let ncProductosCaixa = []; let remProductosCaixa = []; let autoProductosCaixa = []; let graficoAtual = null; let html5QrCode = null; let campoDestinoScanner = ''; let totalDaVendaAtual = 0; let totalNCTela = 0; let descuentoPorcentaje = 0; let filaContingencia = JSON.parse(localStorage.getItem('nube_fila') || '[]'); let itensEntrada = []; let ultimoCDCGerado = ''; let ultimoQRGerado = ''; let ultimoLinkSifen = ''; let contextoCatalogo = ''; let usuariosEquipo = []; 

// VARIÁVEIS PARA O PIX
let radarPix = null;
let pixJaFoiConfirmado = false; 
let pixCopiaEColaAtual = "";

// O MOTOR DO RADAR
function iniciarRadarPix(pagamentoId) {
    clearInterval(radarPix); 
    radarPix = setInterval(async () => {
        try {
            const resposta = await fetch(`/status-pix/${pagamentoId}`, {
                method: 'GET',
                headers: { 'X-Empresa-ID': empresaAtualId.toString() }
            });
            const dados = await resposta.json();
            
            if (dados.sucesso && dados.status === "approved") {
                clearInterval(radarPix);
                showToast("✅ Pago Aprobado!");
                fecharModalPix();
                
                document.getElementById('checkout-metodo').value = "Pix Confirmado";
                pixJaFoiConfirmado = true;
                confirmarVenta(); 
            }
        } catch (erro) {
            console.log("Aguardando pagamento...");
        }
    }, 5000);
}

const getSaaSHeaders = (extraHeaders = {}) => { return { 'Content-Type': 'application/json', 'X-Empresa-ID': empresaAtualId ? empresaAtualId.toString() : "1", ...extraHeaders }; };
    
document.addEventListener("DOMContentLoaded", () => {
    const hoje = new Date();
    const hojeStr = hoje.toISOString().split('T')[0];
    const hojeMenos30 = new Date();
    hojeMenos30.setDate(hoje.getDate() - 30);
    const hojeMenos30Str = hojeMenos30.toISOString().split('T')[0];
    
    // Preenche datas padrão (últimos 30 dias)
    const camposData = {
        'filtro-data-inicio-cierre': hojeMenos30Str,
        'filtro-data-fim-cierre': hojeStr,
        'filtro-data-inicio-var': hojeMenos30Str,
        'filtro-data-fim-var': hojeStr,
        'entrada-data': hojeStr,
        'filtro-data-inicio-stocktake': hojeMenos30Str,
        'filtro-data-fim-stocktake': hojeStr
    };
    
    for (const [id, valor] of Object.entries(camposData)) {
        const el = document.getElementById(id);
        if (el) el.value = valor;
    }
    
    // Carrega automaticamente os relatórios se a tela já estiver visível (ex.: ao recarregar página)
    if (document.getElementById('tela-cierre') && !document.getElementById('tela-cierre').classList.contains('hidden')) {
        carregarCierreCaja();
    }
    if (document.getElementById('tela-variancia') && !document.getElementById('tela-variancia').classList.contains('hidden')) {
        carregarRelatorioVariancia();
    }
    if (document.getElementById('tela-stocktake') && !document.getElementById('tela-stocktake').classList.contains('hidden')) {
        carregarStockTake();
    }
    
    // Event listener para botão Filtrar da Varianza (caso o onclick não funcione)
    const btnFiltrarVariancia = document.querySelector('button[onclick*="carregarRelatorioVariancia"]');
    if (btnFiltrarVariancia) {
        btnFiltrarVariancia.addEventListener('click', carregarRelatorioVariancia);
    }
    
    const toggleStock = document.getElementById('auto-mover-stock');
    if(toggleStock) { toggleStock.addEventListener('change', function() { document.getElementById('auto-stock-status').innerText = this.checked ? "SÍ, añadir al stock" : "NO, es solo un gasto"; document.getElementById('auto-stock-status').className = this.checked ? "text-sm font-bold text-orange-400" : "text-sm font-bold text-gray-500"; }); }
    
    // Garantir que os containers principais estejam visíveis (força remoção de hidden)
    const containers = ['app-screen', 'mobile-header'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('hidden');
            el.classList.remove('d-none');
        }
    });
});

async function fazerLogin() { 
    const ruc = document.getElementById('login-ruc').value.trim(); const senha = document.getElementById('login-senha').value; 
    const btn = document.getElementById('btn-login'); const erroBox = document.getElementById('erro-login'); 
    if(!ruc || !senha) { erroBox.innerText = "Complete todos los campos."; erroBox.classList.remove('hidden'); return; } 
    btn.innerText = "Verificando..."; btn.disabled = true; 
    try { 
        const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ruc: ruc, senha: senha}) }); 
        if (res.ok) { 
            const dados = await res.json(); empresaAtualId = dados.empresa_id; rolUsuario = dados.rol; planoAtivo = dados.plano || 'Inicial'; rucAtual = ruc; 
            if (dados.funcionario_id) { 
                funcionarioId = dados.funcionario_id; 
                nomeFuncionario = dados.nome || ''; 
            } 
            document.getElementById('login-screen').classList.add('hidden'); 
            if (rolUsuario === 'superadmin') { 
                document.getElementById('app-screen').classList.add('hidden'); document.getElementById('superadmin-screen').classList.remove('hidden'); 
                // Ensure dashboard view is active
                setTimeout(() => { if (typeof adminMudarView === 'function') adminMudarView('dashboard'); }, 100);
                carregarEmpresasSaaS(); showToast("¡Bienvenido al Panel Super Admin!"); 
            } else { 
                document.getElementById('app-screen').classList.remove('hidden'); document.getElementById('app-screen').classList.add('flex'); document.getElementById('mobile-header').classList.remove('hidden'); 
                // Mapeia rótulo amigável do perfil
                let etiquetaPerfil = 'Cajero';
                if (rolUsuario === PERFIL_OWNER) etiquetaPerfil = 'Dueño';
                else if (rolUsuario === PERFIL_MANAGER) etiquetaPerfil = 'Gerente';
                document.getElementById('sidebar-rol-loja').innerText = `${etiquetaPerfil} | Plan ${planoAtivo.split(' ')[0]}`; 
                
                const idsTodos = ['nav-group-inventario','nav-btn-dashboard','nav-group-reportes','btn-nav-stocktake','btn-nav-stocktakereport','btn-nav-proveedores','btn-nav-entrada','btn-nav-remision','btn-nav-autofactura','btn-nav-variancia','nav-btn-config','nav-btn-ayuda','btn-cerrar-turno'];
                idsTodos.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = ''; });
                if(document.getElementById('box-novo-prov')) document.getElementById('box-novo-prov').style.display = 'block';

                const isInicial = planoAtivo.includes('Inicial'); const isCrecimiento = planoAtivo.includes('Crecimiento');
                const isLite = planoAtivo.includes('Lite'); const isLitePremium = planoAtivo.includes('Lite Premium');
                
                if (isInicial && rolUsuario === 'admin') {
                    const idsOcultarInicial = ['nav-btn-dashboard', 'btn-nav-stocktake', 'btn-nav-stocktakereport', 'btn-nav-variancia', 'btn-nav-proveedores', 'btn-nav-entrada'];
                    idsOcultarInicial.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; });
                    if(document.getElementById('box-novo-prov')) document.getElementById('box-novo-prov').style.display = 'none';
                } 
                if (isCrecimiento && rolUsuario === 'admin') { 
                    const el1 = document.getElementById('btn-nav-stocktakereport'); if(el1) el1.style.display = 'none'; 
                    const el2 = document.getElementById('btn-nav-variancia'); if(el2) el2.style.display = 'none';
                }
                if (isLite || isLitePremium) {
                    // Ocultar elementos relacionados a SIFEN/Facturación
                    const idsFiscales = ['btn-nav-autofactura', 'btn-nav-remision'];
                    idsFiscales.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; });
                }
                if (rolUsuario === 'cajero') { 
                    const idsCajero = ['nav-group-inventario','nav-btn-dashboard','nav-group-reportes','nav-btn-config','btn-cerrar-turno'];
                    idsCajero.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; }); 
                } 
                
                if (rolUsuario === 'gerente') {
                    const el = document.getElementById('nav-btn-config');
                    if (el) el.style.display = 'none';
                }
                
                await carregarConfiguracao(); await carregarCategorias(); if(!isInicial) await carregarProveedores(); await carregarEstoque(); checarStatusCaixa(); atualizarStatusConexao(); 
                // Pré-carrega dados do dashboard em segundo plano
                setTimeout(() => carregarDashboardComVisibilidade(), 500);
                showToast(`¡Sesión Iniciada!`);
                ajustarCamposFiscais(); // Ajusta obrigatoriedade do RUC conforme plano 
            } 
        } else { const err = await res.json(); erroBox.innerText = err.detail || err.mensagem || "Credenciales incorrectas."; erroBox.classList.remove('hidden'); } 
    } catch(e) { erroBox.innerText = "Error de red."; erroBox.classList.remove('hidden'); } finally { btn.innerText = "Ingresar al Sistema"; btn.disabled = false; } 
}

function prepararTicket(empresaNome, rucEmissor, cdc, cliente, itens, total, qrcode, dataEmissao) {
    let html = `
    <div style="text-align: center; margin-bottom: 10px; font-family: monospace; color: black;">
        <strong style="font-size: 16px;">${empresaNome}</strong><br>
        RUC: ${rucEmissor}<br>
        ${(planoAtivo.includes('Lite') || planoAtivo.includes('Lite Premium')) ? 'Comprobante de Venta Interno<br>' : 'Factura Electrónica (KuDE)<br>'}
        --------------------------------<br>
        CDC:<br>${cdc}<br>
        Fecha: ${dataEmissao}<br>
        Cliente: ${cliente}<br>
        --------------------------------
    </div>
    <table style="width: 100%; font-family: monospace; font-size: 12px; color: black; margin-bottom: 10px;">
        <thead><tr><th style="text-align:left">Cant</th><th style="text-align:left">Desc</th><th style="text-align:right">Total</th></tr></thead>
        <tbody>`;
    itens.forEach(i => {
        html += `<tr><td style="vertical-align:top">${i.quantidade}x</td><td style="vertical-align:top">${i.descricao.substring(0,15)}</td><td style="text-align:right; vertical-align:top">${(i.quantidade * i.preco_unitario).toLocaleString('es-PY')}</td></tr>`;
    });
    html += `
        </tbody>
    </table>
    <div style="text-align: right; font-family: monospace; font-size: 14px; font-weight: bold; border-top: 1px dashed black; padding-top: 5px; color: black;">
        TOTAL: Gs. ${total.toLocaleString('es-PY')}
    </div>
    <div style="text-align: center; margin-top: 15px;">
        ${qrcode && qrcode.trim() !== '' ? `
        <img src="${qrcode}" style="width: 150px; height: 150px; margin: 0 auto; display: block;">
        <p style="font-family: monospace; font-size: 10px; margin-top: 5px; color: black;">Consulte mediante el código QR</p>
        ` : ''}
        ${(planoAtivo.includes('Lite') || planoAtivo.includes('Lite Premium')) ? '<p style="font-family: monospace; font-size: 10px; margin-top: 5px; color: black; font-style: italic;">Este documento es de uso interno y no tiene validez fiscal.</p>' : ''}
        <p style="font-family: monospace; font-size: 10px; margin-top: 10px; color: black;">¡Gracias por su preferencia!</p>
    </div>`;
    document.getElementById('print-area').innerHTML = html;
}

function imprimirTicketLocal() {
    const empresaNome = document.getElementById('sidebar-nome-loja').innerText;
    const rucEmissor = document.getElementById('ruc').value || "S/RUC";
    const cliente = document.getElementById('cliente').value || "Consumidor Final";
    const dataAgora = new Date().toLocaleString('es-PY');
    prepararTicket(empresaNome, rucEmissor, ultimoCDCGerado, cliente, productosCaixa, totalDaVendaAtual, ultimoQRGerado, dataAgora);
    
    document.getElementById('print-area').classList.remove('hidden');
    window.print();
    document.getElementById('print-area').classList.add('hidden');
}

async function imprimirTicketHistorico(cdc) {
    try {
        const res = await fetch(`/api/nota/${cdc}`, {headers: getSaaSHeaders()});
        if(res.ok) {
            const nota = await res.json();
            const empresaNome = document.getElementById('sidebar-nome-loja').innerText;
            prepararTicket(empresaNome, nota.ruc_emissor, cdc, nota.nome_cliente, nota.itens, nota.valor_total, nota.link_qrcode, nota.data_emissao);
            
            document.getElementById('print-area').classList.remove('hidden');
            window.print();
            document.getElementById('print-area').classList.add('hidden');
        } else { showToast("Error", "error"); }
    } catch(e) { showToast("Error", "error"); }
}

function ajustarCamposFiscais() {
    const campoRuc = document.getElementById('ruc');
    if (!campoRuc) return;
    
    const isLite = planoAtivo.includes('Lite');
    const isLitePremium = planoAtivo.includes('Lite Premium');
    
    if (isLite || isLitePremium) {
        // Remover obrigatoriedade
        campoRuc.removeAttribute('required');
        campoRuc.placeholder = 'Opcional (uso interno)';
        // Se estiver vazio, preencher com valor padrão
        if (!campoRuc.value.trim()) {
            campoRuc.value = 'S/RUC';
        }
    } else {
        // Restaurar obrigatoriedade para planos fiscais
        campoRuc.setAttribute('required', 'required');
        campoRuc.placeholder = 'RUC del cliente';
        if (campoRuc.value === 'S/RUC') {
            campoRuc.value = '';
        }
    }
}

function enviarWhatsApp() {
    if (!ultimoLinkSifen) {
        showToast("Error: No hay enlace de factura disponible.", "error");
        return;
    }
    const numero = prompt("Ingrese el número de WhatsApp del cliente\n(Ejemplo con código de país: 5959...):");
    if (numero) {
        const numLimpio = numero.replace(/\D/g, '');
        if (numLimpio.length < 8) {
            showToast("Número inválido.", "error");
            return;
        }
        const isLite = planoAtivo.includes('Lite');
        const isLitePremium = planoAtivo.includes('Lite Premium');
        const mensajeFactura = (isLite || isLitePremium) ? "Comprobante de Venta Interno" : "Factura (KuDE)";
        const texto = encodeURIComponent(`¡Hola! Gracias por su compra. Aquí tiene el enlace a su ${mensajeFactura}: ` + ultimoLinkSifen);
        const url = `https://wa.me/${numLimpio}?text=${texto}`;
        
        const novaAba = window.open(url, '_blank');
        if (!novaAba || novaAba.closed || typeof novaAba.closed === 'undefined') {
            window.location.href = url;
        }
    }
}

function abrirAuthSupervisor() { document.getElementById('modal-auth-supervisor').classList.remove('hidden'); document.getElementById('modal-auth-supervisor').classList.add('flex'); document.getElementById('auth-admin-senha').focus(); }
function fecharAuthSupervisor() { document.getElementById('modal-auth-supervisor').classList.add('hidden'); document.getElementById('modal-auth-supervisor').classList.remove('flex'); document.getElementById('auth-admin-senha').value=''; }
async function validarSupervisor() {
    const senha = document.getElementById('auth-admin-senha').value;
    if(!senha) return;
    try {
        const res = await fetch('/validar-admin', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify({senha}) });
        if(res.ok) {
            fecharAuthSupervisor();
            mudarTela('operaciones', null);
            switchOpTab('nc');
            showToast("✅ Autorizado.");
        } else { showToast("❌ Contraseña incorrecta.", "error"); }
    } catch(e) { showToast("❌ Error.", "error"); }
}

function switchOpTab(tab) {
    const isInicial = planoAtivo.includes('Inicial');
    document.getElementById('op-nc-content').classList.add('hidden');
    document.getElementById('op-merma-content').classList.add('hidden');
    document.getElementById('tab-nc-btn').className = "flex-1 bg-slate-800 text-gray-400 font-bold py-3 rounded-lg border border-slate-700 hover:bg-slate-700 transition";
    document.getElementById('tab-merma-btn').className = "flex-1 bg-slate-800 text-gray-400 font-bold py-3 rounded-lg border border-slate-700 hover:bg-slate-700 transition";
    
    if(isInicial) document.getElementById('tab-merma-btn').style.display = 'none';

    if(tab === 'nc') {
        document.getElementById('op-nc-content').classList.remove('hidden');
        document.getElementById('op-nc-content').classList.add('block');
        document.getElementById('tab-nc-btn').className = "flex-1 bg-purple-600 text-white font-bold py-3 rounded-lg shadow-md transition";
    } else if (tab === 'merma' && !isInicial) {
        document.getElementById('op-merma-content').classList.remove('hidden');
        document.getElementById('op-merma-content').classList.add('block');
        document.getElementById('tab-merma-btn').className = "flex-1 bg-red-600 text-white font-bold py-3 rounded-lg shadow-md transition";
        carregarMermas();
    }
}

function abrirModalEditarEmpresa(id, planoAtual, valorAtual) { 
    document.getElementById('edit-empresa-id').value = id; 
    let p = document.getElementById('edit-plano'); 
    let planoValor = 'Inicial'; // default
    if (planoAtual.includes('Lite Premium')) {
        planoValor = 'Lite Premium';
    } else if (planoAtual.includes('Lite')) {
        planoValor = 'Lite';
    } else if (planoAtual.includes('Crecimiento')) {
        planoValor = 'Crecimiento';
    } else if (planoAtual.includes('VIP')) {
        planoValor = 'VIP';
    } else if (planoAtual.includes('Inicial')) {
        planoValor = 'Inicial';
    }
    p.value = planoValor; 
    document.getElementById('edit-valor').value = valorAtual; 
    document.getElementById('modal-editar-empresa').classList.remove('hidden'); 
    document.getElementById('modal-editar-empresa').classList.add('flex'); 
}
function fecharModalEditarEmpresa() { document.getElementById('modal-editar-empresa').classList.add('hidden'); document.getElementById('modal-editar-empresa').classList.remove('flex'); }
async function salvarEdicaoEmpresa() { const id = document.getElementById('edit-empresa-id').value; const plano = document.getElementById('edit-plano').value; const valor = parseFloat(document.getElementById('edit-valor').value) || 0; try { const res = await fetch(`/super-admin/editar-empresa/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({plano: plano, valor_mensalidade: valor}) }); if(res.ok) { showToast("✅ Plan actualizado."); fecharModalEditarEmpresa(); carregarEmpresasSaaS(); } else { showToast("❌ Error.", "error"); } } catch(e) { showToast("❌ Error.", "error"); } }
async function carregarEmpresasSaaS() { 
    try { 
        const resMet = await fetch('/super-admin/metricas'); 
        if (resMet.ok) { 
            const met = await resMet.json(); 
            document.getElementById('saas-mrr').innerText = met.mrr.toLocaleString('es-PY'); 
            document.getElementById('saas-ativos').innerText = met.clientes_ativos; 
            document.getElementById('saas-vencidos').innerText = met.clientes_vencidos; 
        } 
        const res = await fetch('/super-admin/empresas'); 
        if (res.ok) { 
            const empresas = await res.json(); 
            const tbody = document.getElementById('tabela-saas'); 
            tbody.innerHTML = ''; 
            empresas.forEach(emp => { 
                let corStatus = emp.status === 'Activo' ? 'text-green-400' : 'text-red-400'; 
                // ADICIONAMOS O BOTÃO "COBRAR" BEM AQUI NO FINAL DA LINHA ABAIXO:
                tbody.innerHTML += `<tr class="border-b border-slate-700"><td class="p-4 font-bold text-white">${emp.nome}</td><td class="p-4">${emp.ruc}</td><td class="p-4">${emp.plano}</td><td class="p-4 ${corStatus}">${emp.status}</td><td class="p-4 flex gap-3"><button onclick="abrirModalEditarEmpresa(${emp.id}, '${emp.plano}', ${emp.valor})" class="text-blue-400 font-bold hover:underline">Editar</button> <button onclick="gerarFaturaSaaS(${emp.id})" class="text-brand-accent font-bold hover:underline">Generar Factura</button></td></tr>`; 
            }); 
        } 
        
        // Puxa as faturas assim que carrega as empresas
        carregarFaturasSaaS();
        
    } catch(e) {} 
}

async function criarEmpresaSaaS() {
    const nome = document.getElementById('sa-nome').value.trim();
    const ruc = document.getElementById('sa-ruc').value.trim();
    const plano = document.getElementById('sa-plano').value;
    const valor = parseFloat(document.getElementById('sa-valor').value) || 0;
    const senha_admin = document.getElementById('sa-pass-admin').value.trim();
    
    if (!nome || !ruc || !plano || !senha_admin) {
        showToast("Complete todos los campos requeridos.", "error");
        return;
    }
    
    try {
        const res = await fetch('/super-admin/criar-empresa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome,
                ruc,
                senha_admin,
                senha_caixa: "",
                plano,
                valor_mensalidade: valor
            })
        });
        
        if (res.ok) {
            showToast("Empresa creada exitosamente.");
            // Limpar campos
            document.getElementById('sa-nome').value = '';
            document.getElementById('sa-ruc').value = '';
            document.getElementById('sa-valor').value = '';
            document.getElementById('sa-pass-admin').value = '';
            // Recarregar lista
            carregarEmpresasSaaS();
        } else {
            const err = await res.json();
            showToast(err.detail || "Error al crear empresa", "error");
        }
    } catch (error) {
        console.error('Error:', error);
        showToast("Error de conexión", "error");
    }
}

function exportarTabelaParaCSV(idTbody, nomeBase) { const tbody = document.getElementById(idTbody); if(!tbody) return; let csv = []; const linhas = tbody.closest('table').querySelectorAll('tr'); for(let i=0;i<linhas.length;i++){ let l=[]; const cols = linhas[i].querySelectorAll('td, th'); for(let j=0;j<cols.length;j++) l.push('"'+cols[j].innerText.replace(/"/g,'""')+'"'); csv.push(l.join(',')); } const blob = new Blob(["\uFEFF"+csv.join('\n')], {type:'text/csv;charset=utf-8;'}); const link=document.createElement("a"); link.href=URL.createObjectURL(blob); link.download=`${nomeBase}.csv`; link.click(); }
function abrirModalLegal() { document.getElementById('modal-legal').classList.remove('hidden'); document.getElementById('modal-legal').classList.add('flex'); } function fecharModalLegal() { document.getElementById('modal-legal').classList.add('hidden'); document.getElementById('modal-legal').classList.remove('flex'); }
function fecharModalAudit() { document.getElementById('modal-audit-details').classList.add('hidden'); document.getElementById('modal-audit-details').classList.remove('flex'); }
function atualizarStatusConexao() { const badge = document.getElementById('badge-conexao'); if (navigator.onLine) { badge.className = "bg-green-900/30 text-green-400 px-3 py-1 rounded-full text-xs font-bold"; badge.innerHTML = `Online`; if (filaContingencia.length > 0) sincronizarFila(); } else { badge.classList.remove('hidden'); badge.className = "bg-red-900/30 text-red-400 px-3 py-1 rounded-full text-xs font-bold animate-pulse"; badge.innerHTML = `Offline (${filaContingencia.length})`; } } window.addEventListener('online', atualizarStatusConexao); window.addEventListener('offline', atualizarStatusConexao);
function showToast(message, type = 'success') { const container = document.getElementById('toast-container'); const toast = document.createElement('div'); toast.className = `text-white p-4 rounded-lg shadow-lg min-w-[300px] toast-enter relative overflow-hidden ${type==='success'?'bg-brand-accent':(type==='error'?'bg-red-600':'bg-yellow-500')}`; toast.innerHTML = `<p class="font-bold text-sm">${message}</p>`; container.appendChild(toast); requestAnimationFrame(() => { toast.classList.remove('toast-enter'); toast.classList.add('toast-enter-active'); }); setTimeout(() => { toast.classList.remove('toast-enter-active'); toast.classList.add('toast-exit-active'); setTimeout(() => container.removeChild(toast), 300); }, 3000); }
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const button = input.nextElementSibling;
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.59 6.59m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path></svg>`;
    } else {
        input.type = 'password';
        button.innerHTML = `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>`;
    }
}
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('-translate-x-full'); document.getElementById('overlay').classList.toggle('hidden'); }
function toggleHubSidebar() { document.getElementById('hub-sidebar').classList.toggle('-translate-x-full'); document.getElementById('hub-overlay').classList.toggle('hidden'); }
function cambiarTabConfig(tabName) {
    // Ocultar todas las pestañas
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.add('hidden'));
    // Mostrar la pestaña seleccionada
    const targetPane = document.getElementById(`tab-${tabName}-content`);
    if (targetPane) targetPane.classList.remove('hidden');
    
    // Actualizar botones de navegación
    document.querySelectorAll('.tab-config').forEach(btn => {
        btn.classList.remove('border-b-2', 'border-brand-accent', 'bg-brand-accent/5', 'text-slate-700');
        btn.classList.add('text-slate-500');
    });
    const activeBtn = document.getElementById(`tab-${tabName}`);
    if (activeBtn) {
        activeBtn.classList.add('border-b-2', 'border-brand-accent', 'bg-brand-accent/5', 'text-slate-700');
        activeBtn.classList.remove('text-slate-500');
    }
    
    // Si se activa la pestaña Equipo, actualizar la UI según el plan
    if (tabName === 'equipo') {
        actualizarUIEquipe();
    }
}
function traduzirCargo(rol) {
    // Converte 'manager' -> 'gerente', 'cashier' -> 'cajero', mantém otros valores
    if (rol === 'manager' || rol === 'Manager') return 'gerente';
    if (rol === 'cashier' || rol === 'Cashier') return 'cajero';
    return rol; // 'cajero', 'gerente', etc.
}

function toggleAcordeao(menuId, setaId) { const menu = document.getElementById(menuId); const seta = document.getElementById(setaId); if(menu.classList.contains('hidden')) { menu.classList.remove('hidden'); menu.classList.add('flex'); seta.innerText = '▲'; } else { menu.classList.add('hidden'); menu.classList.remove('flex'); seta.innerText = '▼'; } }

function calcularMensualidad() {
    const plano = document.getElementById('sa-plano').value;
    const descuento = parseInt(document.getElementById('sa-descuento').value) || 0;
    
    // Precios base por plan (en guaraníes)
    const precios = {
        'Inicial': 140000,
        'Crecimiento': 320000,
        'VIP': 420000,
        'Lite': 80000,
        'Lite Premium': 160000
    };
    
    const precioBase = precios[plano] || 0;
    const descuentoValor = (precioBase * descuento) / 100;
    const precioFinal = precioBase - descuentoValor;
    
    document.getElementById('sa-valor').value = precioFinal;
}

function mudarTela(telaId, elementoBotao) { 
    try {
        document.querySelectorAll('.section-tela').forEach(t => t.classList.add('hidden')); 
        const telaAlvo = document.getElementById('tela-' + telaId);
        if(telaAlvo) {
            telaAlvo.classList.remove('hidden');
            telaAlvo.classList.remove('d-none');
            telaAlvo.style.display = '';
        }
        
        if(elementoBotao !== null) { document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('menu-ativo')); elementoBotao.classList.add('menu-ativo'); } 
        if(window.innerWidth < 768) { document.getElementById('sidebar').classList.add('-translate-x-full'); document.getElementById('overlay').classList.add('hidden'); } 
        
        if(['inventario','pos','entrada','operaciones','remision','autofactura'].includes(telaId)) carregarEstoque();
        if(telaId === 'proveedores' || telaId === 'entrada') carregarProveedores(); if(telaId === 'stocktake') carregarStockTake(); if(telaId === 'stocktakereport') carregarStockTakeReport(); if(telaId === 'variancia') carregarRelatorioVariancia(); if(telaId === 'config') iniciarConfig();
        if(telaId === 'operaciones') { document.getElementById('nc-cdc').value=''; document.getElementById('nc-cliente').value=''; ncProductosCaixa=[]; atualizarInterfaceNC(); document.getElementById('merma-cod').value=''; carregarMermas(); }
        if(telaId === 'remision') { carregarRemisiones(); remProductosCaixa=[]; atualizarInterfaceRemision(); }
        if(telaId === 'autofactura') { carregarAutofacturas(); autoProductosCaixa=[]; atualizarInterfaceAuto(); }
        if(telaId === 'reportes') carregarHistorico(); 
        if(telaId === 'cierre') carregarCierreCaja(); 
        if(telaId === 'config') carregarConfiguracao(); 
        if(telaId === 'categorias') carregarCategorias(); 
        if(telaId === 'dashboard') {
            setTimeout(() => carregarDashboard(), 100);
        } 
        if(telaId === 'pos') {
            checarStatusCaixa();
            ajustarCamposFiscais();
        }
    } catch(e) {
        console.error('mudarTela error:', e);
    }
}

async function checarStatusCaixa() { try { const res = await fetch('/status-caixa', { headers: getSaaSHeaders() }); const status = await res.json(); const bloqueio = document.getElementById('bloqueio-caixa'); const badge = document.getElementById('badge-caixa'); if(!status.aberto) { bloqueio.classList.remove('hidden'); bloqueio.classList.add('flex'); badge.classList.add('hidden'); } else { bloqueio.classList.add('hidden'); badge.classList.remove('hidden'); } } catch(e) {} }
async function abrirTurnoCaixa() { const valor = parseFloat(document.getElementById('valor-abertura-caixa').value) || 0; try { const res = await fetch('/abrir-caixa', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify({valor_inicial: valor}) }); if(res.ok) { showToast("✅ Turno abierto."); checarStatusCaixa(); } } catch(e) {} }
async function fecharTurnoCaixa() { const valor = prompt("Efectivo en gaveta:"); if(valor === null) return; try { const res = await fetch('/fechar-caixa', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify({valor_final: parseFloat(valor)||0}) }); if(res.ok) { showToast("✅ Cerrado."); mudarTela('pos', null); } } catch(e) {} }
function abrirModalSangria() { document.getElementById('modal-sangria').classList.remove('hidden'); document.getElementById('modal-sangria').classList.add('flex'); } function fecharModalSangria() { document.getElementById('modal-sangria').classList.add('hidden'); }
async function salvarSangria() { const valor = parseFloat(document.getElementById('sangria-valor').value) || 0; const motivo = document.getElementById('sangria-motivo').value.trim(); try { const res = await fetch('/registrar-sangria', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify({valor, motivo}) }); if (res.ok) { showToast("✅ Retiro registrado."); fecharModalSangria(); } } catch(e) {} }
function abrirCheckout() { if(productosCaixa.length === 0) return; document.getElementById('checkout-total').innerText = totalDaVendaAtual.toLocaleString('es-PY'); document.getElementById('checkout-metodo').value = "Efectivo"; atualizarTroco(); document.getElementById('modal-checkout').classList.remove('hidden'); document.getElementById('modal-checkout').classList.add('flex'); } function fecharCheckout() { document.getElementById('modal-checkout').classList.add('hidden'); }
function atualizarTroco() { 
    const metodo = document.getElementById('checkout-metodo').value; 
    const boxVuelto = document.getElementById('box-vuelto'); 
    
    if(metodo === "Efectivo") { 
        boxVuelto.classList.remove('hidden'); 
        const recebido = parseFloat(document.getElementById('checkout-recebido').value) || 0; 
        document.getElementById('checkout-vuelto').innerText = Math.max(recebido - totalDaVendaAtual, 0).toLocaleString('es-PY'); 
    } else { 
        boxVuelto.classList.add('hidden'); 
    } 
}

async function confirmarVenta() { 
    const metodoPago = document.getElementById('checkout-metodo').value; 

    if (metodoPago === "Pix" && pixJaFoiConfirmado === false) {
        fecharCheckout(); 
        gerarPixNaTela(totalDaVendaAtual); 
        return; 
    }

    const btn = document.getElementById('btn-confirmar-venta'); btn.disabled = true; 
    const payload = { ruc_emissor: document.getElementById('ruc').value, nome_cliente: document.getElementById('cliente').value || "Consumidor Final", valor_total: totalDaVendaAtual, itens: productosCaixa, metodo_pago: metodoPago }; 
    
    if (!navigator.onLine) { 
        filaContingencia.push(payload); localStorage.setItem('nube_fila', JSON.stringify(filaContingencia)); 
        fecharCheckout(); showToast("🔴 Guardado Offline.", "warning"); return; 
    } 
    try { 
        const res = await fetch('/emitir-nota', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(payload) }); 
        if (!res.ok) throw new Error(); 
        const dados = await res.json(); 
        if (dados.demo_mode) {
            // Modo demo: mostrar alerta, limpar carrinho, fechar checkout
            fecharCheckout();
            alert(dados.mensaje); // ou usar SweetAlert se disponível
            productosCaixa = [];
            atualizarInterfaceCaixa();
            return;
        }
        fecharCheckout(); 
        document.getElementById('resultado').classList.remove('hidden');
        pixJaFoiConfirmado = false; 
        document.getElementById('btn-pdf').href = dados.link_pdf; 
        
        // Verificar se é plano não-fiscal (Lite/Lite Premium) ou venda interna
        const isLite = planoAtivo.includes('Lite');
        const isLitePremium = planoAtivo.includes('Lite Premium');
        const isInterno = dados.interno === true || isLite || isLitePremium;
        
        // Alterar título conforme tipo de comprovante
        const textoResultado = document.getElementById('texto-resultado');
        if (isInterno) {
            textoResultado.textContent = '✅ Venta Registrada';
            textoResultado.classList.remove('text-green-600');
            textoResultado.classList.add('text-blue-600');
        } else {
            textoResultado.textContent = '✅ ¡Factura Aprobada!';
            textoResultado.classList.remove('text-blue-600');
            textoResultado.classList.add('text-green-600');
        }
        
        ultimoCDCGerado = dados.cdc;
        ultimoLinkSifen = window.location.origin + dados.link_pdf; 
        
        // Gerar QR Code apenas para planos fiscais com link válido
        const qrcodeImg = document.getElementById('qrcode-img');
        // Definir ultimoQRGerado (usado para impressão)
        if (dados.link_qrcode && dados.link_qrcode.trim() !== '' && !isInterno) {
            ultimoQRGerado = `https://quickchart.io/qr?text=${encodeURIComponent(dados.link_qrcode)}&size=150`;
            qrcodeImg.src = ultimoQRGerado;
            qrcodeImg.classList.remove('hidden');
        } else {
            // Ocultar QR Code para planos não-fiscais
            ultimoQRGerado = '';
            qrcodeImg.classList.add('hidden');
            qrcodeImg.src = '';
        } 
        
        document.getElementById('btn-emitir').classList.add('hidden'); 
        atualizarInterfaceCaixa(); 
    } catch(e) { showToast("❌ Error.", "error"); } finally { btn.disabled = false; } 
}

function novaVenda() { document.getElementById('resultado').classList.add('hidden'); document.getElementById('btn-emitir').classList.remove('hidden'); document.getElementById('cliente').value = ''; descuentoPorcentaje = 0; productosCaixa = []; atualizarInterfaceCaixa(); }
async function sincronizarFila() { if (filaContingencia.length === 0 || !navigator.onLine) return; let pendentes = [...filaContingencia]; filaContingencia = []; let sucesso = 0; for (let n of pendentes) { try { const res = await fetch('/emitir-nota', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(n) }); if (res.ok) sucesso++; else filaContingencia.push(n); } catch(e) { filaContingencia.push(n); } } localStorage.setItem('nube_fila', JSON.stringify(filaContingencia)); atualizarStatusConexao(); if(sucesso>0) showToast(`✅ ${sucesso} sincronizadas.`); }

function abrirCamera(idCampo) { campoDestinoScanner = idCampo; document.getElementById('camera-modal').classList.remove('hidden'); document.getElementById('camera-modal').classList.add('flex'); if (!html5QrCode) html5QrCode = new Html5Qrcode("reader"); html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 250, height: 150 } }, onScanSucesso, ()=>{}); } 
function onScanSucesso(codigo) { fecharCamera(); document.getElementById(campoDestinoScanner).value = codigo; if (campoDestinoScanner === 'scanner-barras') verificarScanner({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'entrada-scanner') agregarProductoEntrada(codigo); else if (campoDestinoScanner === 'nc-scanner') verificarScannerNC({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'merma-cod') buscarParaMerma({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'rem-scanner') verificarScannerRemision({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'auto-scanner') verificarScannerAuto({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'busca-st') filtrarStockTake(); else if (campoDestinoScanner === 'busca-inventario') { setTimeout(()=>filtrarEstoque(),100); } } 
function fecharCamera() { document.getElementById('camera-modal').classList.add('hidden'); if(html5QrCode) html5QrCode.stop().then(()=>html5QrCode.clear()); }

let isScanning = false; function filtrarPOS() { const input = document.getElementById('scanner-barras').value.toLowerCase(); const dropdown = document.getElementById('pos-dropdown'); dropdown.innerHTML = ''; if (input.length < 2) { dropdown.classList.add('hidden'); return; } const resultados = productosGlobais.filter(p => p.descricao.toLowerCase().includes(input) || p.codigo_barras.toLowerCase().includes(input)).slice(0, 10); if (resultados.length > 0) { dropdown.classList.remove('hidden'); resultados.forEach(p => { const div = document.createElement('div'); div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white'; div.innerHTML = `<span>${p.descricao}</span><span class="text-brand-accent">Gs. ${p.preco_venda.toLocaleString('es-PY')}</span>`; div.onclick = () => seleccionarProductoPOS(p); dropdown.appendChild(div); }); } else { dropdown.classList.add('hidden'); } }
function seleccionarProductoPOS(prod) { document.getElementById('pos-dropdown').classList.add('hidden'); document.getElementById('scanner-barras').value = ''; const idx = productosCaixa.findIndex(p => p.codigo_barras === prod.codigo_barras); if (idx !== -1) productosCaixa[idx].quantidade += 1; else productosCaixa.push({ codigo_barras: prod.codigo_barras, descricao: prod.descricao, quantidade: 1, preco_unitario: parseFloat(prod.preco_venda) }); atualizarInterfaceCaixa(); }
async function verificarScanner(e) { if(e && e.key === 'Enter') { if(e.preventDefault) e.preventDefault(); if(isScanning) return; isScanning = true; const codigo = document.getElementById('scanner-barras').value.trim(); document.getElementById('scanner-barras').value = ''; document.getElementById('pos-dropdown').classList.add('hidden'); try { const idx = productosCaixa.findIndex(p => p.codigo_barras === codigo); if (idx !== -1) { productosCaixa[idx].quantidade += 1; atualizarInterfaceCaixa(); } else { const pGlobal = productosGlobais.find(p=>p.codigo_barras === codigo); if(pGlobal) seleccionarProductoPOS(pGlobal); else { const res = await fetch('/buscar-produto/'+codigo, {headers:getSaaSHeaders()}); if(res.ok) { const p = await res.json(); productosCaixa.push({codigo_barras:codigo, descricao:p.descricao, quantidade:1, preco_unitario:parseFloat(p.preco)}); atualizarInterfaceCaixa(); } } } } catch(err){} finally{ setTimeout(()=>isScanning=false, 300); } } }
function pedirDescuento() { const desc = prompt("Descuento (%):"); if(desc) { descuentoPorcentaje = parseFloat(desc) || 0; atualizarInterfaceCaixa(); } } function alterarQuantidade(idx, delta) { productosCaixa[idx].quantidade += delta; if(productosCaixa[idx].quantidade <= 0) productosCaixa.splice(idx,1); atualizarInterfaceCaixa(); }
function atualizarInterfaceCaixa() { const tbody = document.getElementById('lista-produtos'); tbody.innerHTML = ''; let sub = 0; productosCaixa.forEach((p, i) => { const st = p.quantidade * p.preco_unitario; sub += st; tbody.innerHTML += `<div class="bg-slate-700/50 p-3 rounded-lg flex justify-between items-center mb-2"><div><span class="text-black block" style="color: #000 !important;">${p.descricao}</span></div><div class="flex items-center gap-2"><button onclick="alterarQuantidade(${i},-1)" class="text-brand-accent px-2 font-bold">-</button><span class="text-black" style="color: #000 !important;">${p.quantidade}</span><button onclick="alterarQuantidade(${i},1)" class="text-brand-accent px-2 font-bold">+</button><span class="text-brand-accent w-24 text-right">Gs. ${st.toLocaleString('es-PY')}</span></div></div>`; }); const descV = sub*(descuentoPorcentaje/100); totalDaVendaAtual = sub - descV; document.getElementById('subtotal-tela').innerText = sub.toLocaleString('es-PY'); document.getElementById('descuento-tela').innerText = descV.toLocaleString('es-PY'); document.getElementById('valor-total-tela').innerText = totalDaVendaAtual.toLocaleString('es-PY'); }

function toggleFormProducto() {
    const form = document.getElementById('form-novo-produto');
    const list = document.getElementById('produto-list-wrapper');
    if (!form || !list) return;
    const open = !form.classList.contains('hidden');
    form.classList.toggle('hidden');
    list.classList.toggle('hidden', !open);
    if (!open) {
        const orig = document.getElementById('produto-original-cod');
        if (orig) orig.value = '';
        document.getElementById('novo-cod').disabled = false;
    } else {
        cancelarEdicaoProduto();
    }
} function filtrarEstoque() { const termo=document.getElementById('busca-inventario').value.toLowerCase(); const cat=document.getElementById('filtro-cat-inventario').value; const res=productosGlobais.filter(p=>(p.descricao.toLowerCase().includes(termo)||p.codigo_barras.toLowerCase().includes(termo))&&(cat===""||p.categoria===cat)); const tbody=document.getElementById('tabela-estoque'); tbody.innerHTML=''; res.forEach(p=>{ tbody.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 font-bold text-white">${p.descricao}<br><span class="text-xs text-gray-400 font-mono">${p.codigo_barras}</span></td><td class="p-4">${p.categoria}</td><td class="p-4">${p.codigo_proveedor||'-'}</td><td class="p-4 text-right text-white">Gs. ${p.preco_venda.toLocaleString('es-PY')}</td><td class="p-4 text-center font-bold text-brand-accent">${p.quantidade}</td><td class="p-4"><button onclick="abrirEditarProduto('${p.codigo_barras}')" class="text-blue-400 mr-2">✏️</button><button onclick="deletarProduto('${p.codigo_barras}')" class="text-red-400">🗑️</button></td></tr>`; }); }
function preencherFiltroCategorias() {
    const select = document.getElementById('filtro-cat-inventario');
    if (!select) return;
    const catAtual = select.value;
    select.innerHTML = '';
    const opTodas = document.createElement('option');
    opTodas.value = '';
    opTodas.textContent = 'Todas las Categorías';
    select.appendChild(opTodas);
    const categorias = [...new Set(productosGlobais.map(p => p.categoria).filter(c => c && c.trim() !== ''))].sort();
    categorias.forEach(cat => {
        const op = document.createElement('option');
        op.value = cat;
        op.textContent = cat;
        select.appendChild(op);
    });
    if (catAtual && categorias.includes(catAtual)) {
        select.value = catAtual;
    }
}
async function carregarEstoque() { try { const res = await fetch('/listar-produtos', {headers:getSaaSHeaders()}); const lista = await res.json(); productosGlobais = lista.sort((a, b) => a.descricao.localeCompare(b.descricao)); preencherFiltroCategorias(); filtrarEstoque(); if(document.getElementById('tela-stocktake') && !document.getElementById('tela-stocktake').classList.contains('hidden')) renderTabelaStockTake(productosGlobais); } catch(e){} }
function calcularLucro() { const c = parseFloat(document.getElementById('novo-custo').value)||0; const v = parseFloat(document.getElementById('novo-preco').value)||0; if(v>0 && c>=0) { document.getElementById('info-lucro').innerText = `GP: ${((v-c)/v*100).toFixed(1)}%`; document.getElementById('info-lucro').className="text-green-400 text-xs"; } }
async function cadastrarProduto() { 
    const codigoOriginal = document.getElementById('produto-original-cod').value;
    const d = { 
        codigo_barras: document.getElementById('novo-cod').value, 
        descricao: document.getElementById('novo-desc').value, 
        categoria: document.getElementById('novo-cat').value, 
        subcategoria: "-", 
        preco_custo: parseFloat(document.getElementById('novo-custo').value)||0, 
        preco_venda: parseFloat(document.getElementById('novo-preco').value)||0, 
        quantidade: parseInt(document.getElementById('novo-qtd').value)||0, 
        codigo_proveedor: document.getElementById('novo-prov')?.value||"" 
    }; 
    try { 
        const url = codigoOriginal ? `/editar-produto/${codigoOriginal}` : '/cadastrar-produto';
        const method = codigoOriginal ? 'PUT' : 'POST';
        await fetch(url, {method, headers:getSaaSHeaders(), body:JSON.stringify(d)}); 
        carregarEstoque(); 
        toggleFormProducto(); 
        cancelarEdicaoProduto();
    } catch(e){} 
}
function abrirEditarProduto(codigo) {
    const produto = productosGlobais.find(p => p.codigo_barras === codigo);
    if (!produto) return;
    // Preencher campos
    document.getElementById('novo-cod').value = produto.codigo_barras;
    document.getElementById('novo-desc').value = produto.descricao;
    document.getElementById('novo-cat').value = produto.categoria;
    document.getElementById('novo-custo').value = produto.preco_custo;
    document.getElementById('novo-preco').value = produto.preco_venda;
    document.getElementById('novo-qtd').value = produto.quantidade;
    // Proveedor (pode não existir no select, mas tentar)
    const selectProv = document.getElementById('novo-prov');
    if (selectProv) {
        // Se o valor existir no select, selecionar; caso contrário, definir valor e texto?
        // Por enquanto apenas setar valor
        selectProv.value = produto.codigo_proveedor || '';
    }
    // Guardar código original
    document.getElementById('produto-original-cod').value = produto.codigo_barras;
    // Desabilitar edição do código (não pode mudar a chave)
    document.getElementById('novo-cod').disabled = true;
    // Alterar texto do botão
    const btnGuardar = document.querySelector('#form-novo-produto button[onclick="cadastrarProduto()"]');
    if (btnGuardar) btnGuardar.textContent = 'Actualizar Producto';
    // Mostrar botão de cancelar edição (se existir)
    const btnCancelarEdit = document.getElementById('btn-cancelar-edicao');
    if (btnCancelarEdit) btnCancelarEdit.classList.remove('hidden');
    // Exibir formulário se estiver oculto
    document.getElementById('form-novo-produto').classList.remove('hidden');
    // Ocultar lista
    const list = document.getElementById('produto-list-wrapper');
    if (list) list.classList.add('hidden');
}
function cancelarEdicaoProduto() {
    // Hide form, show list
    const form = document.getElementById('form-novo-produto');
    if (form) form.classList.add('hidden');
    const list = document.getElementById('produto-list-wrapper');
    if (list) list.classList.remove('hidden');
    // Reset fields
    const orig = document.getElementById('produto-original-cod');
    if (orig) orig.value = '';
    document.getElementById('novo-cod').disabled = false;
    document.getElementById('novo-cod').value = '';
    document.getElementById('novo-desc').value = '';
    document.getElementById('novo-cat').value = '';
    document.getElementById('novo-custo').value = '';
    document.getElementById('novo-preco').value = '';
    document.getElementById('novo-qtd').value = '';
    const selectProv = document.getElementById('novo-prov');
    if (selectProv) selectProv.value = '';
    const btnGuardar = document.querySelector('#form-novo-produto button[onclick="cadastrarProduto()"]');
    if (btnGuardar) btnGuardar.textContent = 'Guardar Producto';
    const btnCancelarEdit = document.getElementById('btn-cancelar-edicao');
    if (btnCancelarEdit) btnCancelarEdit.classList.add('hidden');
}
async function deletarProduto(cod) { if(confirm("Eliminar?")) { await fetch(`/deletar-produto/${cod}`, {method:'DELETE',headers:getSaaSHeaders()}); carregarEstoque(); } }
async function carregarCierreCaja() {
    const i = document.getElementById('filtro-data-inicio-cierre').value;
    const f = document.getElementById('filtro-data-fim-cierre').value;
    try {
        const res = await fetch(`/cierre-caja?inicio=${i}&fim=${f}`, { headers: getSaaSHeaders() });
        const d = await res.json();
        document.getElementById('cierre-vendas').innerText = 'Gs. ' + d.vendas_hoje.toLocaleString('es-PY');
        const porcentagemStr = (d.vendas_hoje > 0 ? (d.lucro_bruto / d.vendas_hoje * 100) : 0).toFixed(1).replace('.', ',');
        document.getElementById('cierre-gp').innerHTML = 'Gs. ' + d.lucro_bruto.toLocaleString('es-PY') + ' <span class="text-green-500 text-sm font-normal">(' + porcentagemStr + '%)</span>';
        document.getElementById('cierre-sangrias').innerText = 'Gs. ' + d.total_sangrias.toLocaleString('es-PY');
        document.getElementById('cierre-notas').innerText = d.notas_emitidas;
        const tb = document.getElementById('tabela-cierre-itens');
        tb.innerHTML = '';
        d.transacoes.forEach(it => {
            tb.innerHTML += `<tr class="border-b border-slate-700"><td class="p-3 text-white">${it.fecha_hora}</td><td class="p-3 text-center">${it.tipo}</td><td class="p-3 text-right">Gs. ${it.monto.toLocaleString('es-PY')}</td><td class="p-3">${it.detalle}</td></tr>`;
        });
    } catch(e) {}
}

async function carregarHistorico(busca="") { 
    const i=document.getElementById('filtro-data-inicio-hist')?.value||''; 
    const f=document.getElementById('filtro-data-fim-hist')?.value||''; 
    try { 
        const res=await fetch(`/listar-notas?busca=${busca}&inicio=${i}&fim=${f}`, {headers:getSaaSHeaders()}); 
        const d=await res.json(); const tb=document.getElementById('tabela-historico'); tb.innerHTML=''; 
        d.historico.forEach(n=>{ 
            tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-xs font-mono text-gray-400">${n.cdc.substring(0,20)}...</td><td class="p-4 text-white">${n.nome_cliente}</td><td class="p-4 text-right text-brand-accent">Gs. ${n.valor_total.toLocaleString('es-PY')}</td><td class="p-4">${n.metodo_pago}</td><td class="p-4 flex gap-2"><button onclick="imprimirTicketHistorico('${n.cdc}')" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm transition">🖨️ Ticket</button><a href="${n.link_pdf}" target="_blank" class="bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm transition">📄 PDF</a></td></tr>`; 
        }); 
    } catch(e){} 
} 
function buscarNotas() { carregarHistorico(document.getElementById('busca').value); }

// Função auxiliar para aguardar elemento estar visível
// Função wrapper simplificada — sem observer nem timeout que possa travar
async function carregarDashboardComVisibilidade() {
    await new Promise(r => setTimeout(r, 100));
    await carregarDashboard();
}

async function carregarDashboard() { 
    try { 
        // Verificar se é conta Demo (plano Demo ou RUC especial)
        const isDemoAccount = (planoAtivo && (planoAtivo.toLowerCase().includes('demo') || planoAtivo === 'Plan Demo')) || (rucAtual && rucAtual.startsWith('800'));
        
        if (isDemoAccount) {
            // Dados estáticos para conta Demo
            const dashVendas = document.getElementById('dash-vendas');
            const dashNotas = document.getElementById('dash-notas');
            if (dashVendas) dashVendas.innerText = 'Gs. 15.450.000';
            if (dashNotas) dashNotas.innerText = '142';
            
            // Dados mock para gráfico
            const mockTopProdutos = [
                { nome: 'Arroz 1kg', quantidade: 45 },
                { nome: 'Azúcar 1kg', quantidade: 38 },
                { nome: 'Aceite 900ml', quantidade: 32 },
                { nome: 'Harina 1kg', quantidade: 28 },
                { nome: 'Fideos 500g', quantidade: 25 }
            ];
            
            // Renderizar gráfico se canvas disponível
            try {
                const canvas = document.getElementById('grafico-produtos');
                if (canvas) {
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    const ctx = canvas.getContext('2d');
                    if (graficoAtual) graficoAtual.destroy();
                    graficoAtual = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: mockTopProdutos.map(p => p.nome),
                            datasets: [{
                                label: 'Unidades',
                                data: mockTopProdutos.map(p => p.quantidade),
                                backgroundColor: '#0d9488'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            animation: { duration: 500, easing: 'easeOutQuart' }
                        }
                    });
                }
            } catch(e) {
                console.warn('Dashboard canvas render skipped:', e.message);
            }
            return; // Abortar fetch
        }
        
        // Mostrar estado de carregamento
        const dashVendas = document.getElementById('dash-vendas');
        const dashNotas = document.getElementById('dash-notas');
        if (dashVendas) dashVendas.innerText = 'Gs. ...';
        if (dashNotas) dashNotas.innerText = '...';
        
        // Limpar gráfico anterior se existir
        if (graficoAtual) {
            graficoAtual.destroy();
            graficoAtual = null;
        }
        
        const res = await fetch('/dados-dashboard', {headers: getSaaSHeaders()}); 
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d = await res.json(); 
        
        // Atualizar métricas
        if (dashVendas) dashVendas.innerText = 'Gs. ' + d.total_vendas.toLocaleString('es-PY');
        if (dashNotas) dashNotas.innerText = d.total_notas;
        
        // Renderizar gráfico apenas se o canvas estiver disponível
        const canvas = document.getElementById('grafico-produtos');
        if (canvas) {
            try {
                await new Promise(resolve => requestAnimationFrame(resolve));
                const ctx = canvas.getContext('2d');
                if (graficoAtual) graficoAtual.destroy();
                graficoAtual = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: d.top_produtos.map(p => p.nome),
                        datasets: [{
                            label: 'Unidades',
                            data: d.top_produtos.map(p => p.quantidade),
                            backgroundColor: '#0d9488'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {
                            duration: 500,
                            easing: 'easeOutQuart'
                        }
                    }
                });
            } catch(e) {
                console.warn('Canvas render skipped (not ready yet):', e.message);
            }
        }
    } catch(e) {
        console.error('Erro ao carregar dashboard:', e);
        // Mostrar erro nas métricas
        const dashVendas = document.getElementById('dash-vendas');
        const dashNotas = document.getElementById('dash-notas');
        if (dashVendas) dashVendas.innerText = 'Gs. Error';
        if (dashNotas) dashNotas.innerText = 'Error';
        
        // Tentar novamente após 3 segundos
        setTimeout(() => carregarDashboard(), 3000);
    }
}
async function carregarCategorias() { try { const res=await fetch('/listar-categorias', {headers:getSaaSHeaders()}); const d=await res.json(); const sf=document.getElementById('novo-cat'); const sfi=document.getElementById('filtro-cat-inventario'); const sfc=document.getElementById('stocktake-categoria'); const tb=document.getElementById('tabela-categorias'); if(sf) sf.innerHTML=''; if(sfi) sfi.innerHTML='<option value="">Todas</option>'; if(sfc) sfc.innerHTML='<option value="">Todas las categorías</option>'; if(tb) tb.innerHTML=''; d.forEach(c=>{ if(sf) sf.innerHTML+=`<option value="${c.nome}">${c.nome}</option>`; if(sfi) sfi.innerHTML+=`<option value="${c.nome}">${c.nome}</option>`; if(sfc) sfc.innerHTML+=`<option value="${c.nome}">${c.nome}</option>`; if(tb) tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${c.nome}</td><td class="p-4 text-center"><button onclick="deletarCategoria(${c.id})" class="text-red-400">🗑️</button></td></tr>`; }); } catch(e){} }
async function adicionarCategoria() { const n=document.getElementById('nova-cat-nome').value; if(n){ await fetch('/cadastrar-categoria',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({nome:n})}); carregarCategorias(); document.getElementById('nova-cat-nome').value=''; } } async function deletarCategoria(id) { if(confirm("Del?")) { await fetch(`/deletar-categoria/${id}`,{method:'DELETE',headers:getSaaSHeaders()}); carregarCategorias(); } }
async function carregarConfiguracao() { 
    try { 
        console.log("A pedir configurações ao servidor...");
        const res = await fetch('/obter-configuracao', {headers: getSaaSHeaders()}); 
        const d = await res.json(); 
        
        console.log("Dados recebidos da base de dados:", d);

        if(d){ 
            if(document.getElementById('conf-nome')) document.getElementById('conf-nome').value = d.nome_empresa || ''; 
            if(document.getElementById('conf-ruc')) document.getElementById('conf-ruc').value = d.ruc || ''; 
            if(document.getElementById('conf-endereco')) document.getElementById('conf-endereco').value = d.endereco || ''; 
            if(document.getElementById('conf-senha-cert')) document.getElementById('conf-senha-cert').value = d.senha_certificado || ''; 
            if(document.getElementById('conf-csc')) document.getElementById('conf-csc').value = d.csc || ''; 
            
            if(document.getElementById('conf-mp-token')) {
                document.getElementById('conf-mp-token').value = d.mercado_pago_token || ''; 
                console.log("Token colocado na caixinha:", d.mercado_pago_token);
            }
            
            if(document.getElementById('ruc')) document.getElementById('ruc').value = d.ruc || ''; 
            if(document.getElementById('conf-ambiente')) document.getElementById('conf-ambiente').value = d.ambiente_sifen || 'testes'; 
            if(document.getElementById('sidebar-nome-loja')) document.getElementById('sidebar-nome-loja').innerText = d.nome_empresa || 'Empresa'; 
        } 
    } catch(e){
        console.error("Erro ao carregar configurações:", e);
    } 
}

async function salvarConfiguracao() { 
    try {
        const f = new FormData(); 
        f.append('nome_empresa', document.getElementById('conf-nome').value); 
        f.append('ruc', document.getElementById('conf-ruc').value); 
        f.append('endereco', document.getElementById('conf-endereco').value); 
        f.append('senha_certificado', document.getElementById('conf-senha-cert').value); 
        if(document.getElementById('conf-csc')) f.append('csc', document.getElementById('conf-csc').value); 
        
        let tokenParaEnviar = "";
        if(document.getElementById('conf-mp-token')) {
            tokenParaEnviar = document.getElementById('conf-mp-token').value;
            f.append('mercado_pago_token', tokenParaEnviar); 
        }

        console.log("A enviar para o servidor o token:", tokenParaEnviar);

        const resposta = await fetch('/salvar-configuracao', {
            method: 'POST',
            headers: {'X-Empresa-ID': empresaAtualId.toString()},
            body: f
        }); 

        if (resposta.ok) {
            showToast("✅ Configuración General Guardada"); 
        } else {
            showToast("❌ Error al guardar en el servidor");
            console.error("O servidor rejeitou:", await resposta.text());
        }
    } catch(e) {
        showToast("❌ Error de conexión");
        console.error("Erro ao enviar:", e);
    }
}
async function alterarAmbienteSifen() { await fetch('/alternar-ambiente',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({ambiente:document.getElementById('conf-ambiente').value})}); }


async function fazerUploadCertificado() { const file=document.getElementById('arquivo-cert').files[0]; if(file){ const f=new FormData(); f.append('arquivo',file); await fetch('/upload-certificado',{method:'POST',headers:{'X-Empresa-ID':empresaAtualId.toString()},body:f}); showToast("✅ Subido"); } }
async function carregarStockTake() { await carregarEstoque(); await carregarCategorias(); await carregarProveedores(); filtrarStockTake(); } function filtrarStockTake() {
    const texto = document.getElementById('busca-st').value.toLowerCase();
    const categoria = document.getElementById('stocktake-categoria').value;
    const proveedor = document.getElementById('stocktake-proveedor').value;
    const filtrados = productosGlobais.filter(p => {
        if (texto && !p.descricao.toLowerCase().includes(texto) && !p.codigo_barras.toLowerCase().includes(texto)) return false;
        if (categoria && p.categoria !== categoria) return false;
        if (proveedor && p.codigo_proveedor !== proveedor) return false;
        return true;
    });
    renderTabelaStockTake(filtrados);
}
function filtrarListaStockTake() { filtrarStockTake(); } function renderTabelaStockTake(l) { const tb=document.getElementById('tabela-stocktake'); tb.innerHTML=''; l.forEach(p=>{ let val=document.getElementById(`st-input-${p.codigo_barras}`)?.value||''; tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${p.descricao}</td><td class="p-4 text-center font-bold text-brand-accent">${p.quantidade}</td><td class="p-4 text-center"><input type="number" id="st-input-${p.codigo_barras}" value="${val}" class="w-24 p-2 bg-white text-center text-slate-800 border border-slate-300 rounded outline-none focus:ring-2 focus:ring-brand-accent" oninput="atualizarDiffST('${p.codigo_barras}',${p.quantidade})"></td><td class="p-4 text-center"><span id="st-diff-${p.codigo_barras}">-</span></td></tr>`; if(val!=='') atualizarDiffST(p.codigo_barras,p.quantidade); }); } function atualizarDiffST(c,q) { let val=document.getElementById(`st-input-${c}`).value; let sp=document.getElementById(`st-diff-${c}`); if(val==='') sp.innerText='-'; else { let d=parseInt(val)-q; sp.innerText=d>0?`+${d}`:d; sp.className=d>0?'text-green-400 font-bold':(d<0?'text-red-400 font-bold':'text-gray-400 font-bold'); } } async function salvarStockTake() { let pay=[]; productosGlobais.forEach(p=>{ let v=document.getElementById(`st-input-${p.codigo_barras}`); if(v&&v.value!=='') if(parseInt(v.value)!==p.quantidade) pay.push({codigo_barras:p.codigo_barras,qtd_fisica:parseInt(v.value)}); }); if(pay.length>0) { await fetch('/salvar-auditoria',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({itens:pay})}); showToast("✅ Audit OK"); carregarStockTake(); } }

async function carregarRelatorioVariancia() { 
    const i=document.getElementById('filtro-data-inicio-var').value; 
    const f=document.getElementById('filtro-data-fim-var').value; 
    try { 
        const res=await fetch(`/relatorio-variancia?inicio=${i}&fim=${f}`, {headers:getSaaSHeaders()}); 
        const d=await res.json(); 
        const tb=document.getElementById('tabela-variancia'); 
        tb.innerHTML=''; 
        let imp=0; 
        let un=0; 
        if(d.length===0){ 
            tb.innerHTML='<tr><td colspan="6" class="text-center p-6 text-gray-500">Nada</td></tr>'; 
            document.getElementById('var-impacto-total').innerText='Gs. 0'; 
            document.getElementById('var-unidades-total').innerText=0; 
            return; 
        } 
        d.forEach(x=>{ 
            imp+=x.impacto_financeiro; 
            un+=x.total_unidades; 
            let c = x.impacto_financeiro>0?'text-green-400':'text-red-400'; 
            tb.innerHTML+=`<tr class="border-b border-slate-700">
                <td class="p-3 text-gray-400 text-xs">${x.fecha}</td>
                <td class="p-3 text-white font-bold">${x.codigo}</td>
                <td class="p-3 text-gray-400">${x.tipo}</td>
                <td class="p-3 text-white">${x.descricao}</td>
                <td class="p-3 text-center font-bold ${c}">${x.total_unidades}</td>
                <td class="p-3 text-right font-bold ${c}">Gs. ${x.impacto_financeiro.toLocaleString('es-PY')}</td>
            </tr>`; 
        }); 
        document.getElementById('var-unidades-total').innerText=un; 
        document.getElementById('var-impacto-total').innerText=`Gs. ${imp.toLocaleString('es-PY')}`; 
        document.getElementById('var-impacto-total').className=`text-3xl font-bold ${imp>0?'text-green-400':'text-red-400'}`; 
    } catch(e){} 
}

async function carregarStockTakeReport() {
    try {
        // Usar intervalo padrão dos últimos 30 dias
        const hoje = new Date();
        const fim = hoje.toISOString().split('T')[0];
        const inicio = new Date(hoje.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        const res = await fetch(`/listar-auditorias?inicio=${inicio}&fim=${fim}`, {headers: getSaaSHeaders()});
        const d = await res.json();
        const tb = document.getElementById('tabela-stocktakereport');
        if (!tb) return;
        tb.innerHTML = '';
        if (d.length === 0) {
            tb.innerHTML = '<tr><td colspan="4" class="text-center p-6 text-gray-500">No hay auditorías registradas</td></tr>';
            return;
        }
        d.forEach(a => {
            const data = a.data.split(' ')[0]; // YYYY-MM-DD
            const impacto = a.impacto_financeiro;
            const items = a.total_itens;
            const color = impacto > 0 ? 'text-red-400' : (impacto < 0 ? 'text-green-400' : 'text-gray-400');
            tb.innerHTML += `<tr class="border-b border-slate-700">
                <td class="p-4 text-gray-400">${data}</td>
                <td class="p-4 text-center font-bold text-white">${items}</td>
                <td class="p-4 text-right font-bold ${color}">Gs. ${Math.abs(impacto).toLocaleString('es-PY')}</td>
                <td class="p-4 text-center"><button onclick="verDetalhesAuditoria(${a.id})" class="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-white text-sm font-bold">🔍</button></td>
            </tr>`;
        });
    } catch(e) { console.error(e); }
}

async function verDetalhesAuditoria(auditoriaId) {
    try {
        const res = await fetch(`/detalhes-auditoria/${auditoriaId}`, {headers: getSaaSHeaders()});
        const itens = await res.json();
        const tb = document.getElementById('tabela-audit-detalhes');
        if (!tb) return;
        tb.innerHTML = '';
        itens.forEach(i => {
            const cor = i.diferenca > 0 ? 'text-green-400' : (i.diferenca < 0 ? 'text-red-400' : 'text-gray-400');
            tb.innerHTML += `<tr class="border-b border-slate-700">
                <td class="p-3 text-white">${i.descricao}</td>
                <td class="p-3 text-center font-bold text-white">${i.qtd_sistema}</td>
                <td class="p-3 text-center font-bold ${cor}">${i.qtd_fisica}</td>
                <td class="p-3 text-center font-bold ${cor}">${i.diferenca > 0 ? '+' : ''}${i.diferenca}</td>
                <td class="p-3 text-right font-bold ${cor}">Gs. ${i.impacto.toLocaleString('es-PY')}</td>
            </tr>`;
        });
        document.getElementById('modal-audit-details').classList.remove('hidden');
        document.getElementById('modal-audit-details').classList.add('flex');
    } catch(e) { console.error(e); }
}

async function carregarRemisiones() {
    // Función temporal para evitar error de referencia
    console.log('carregarRemisiones placeholder');
}

function atualizarInterfaceRemision() {
    const tbody = document.getElementById('tabela-remision-itens');
    tbody.innerHTML = '';
    if (remProductosCaixa.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="p-6 text-center text-slate-400">Ningún producto agregado.</td></tr>';
        return;
    }
    remProductosCaixa.forEach((p, i) => {
        const row = document.createElement('tr');
        row.className = 'border-b border-slate-100 hover:bg-slate-50';
        row.innerHTML = `
            <td class="p-3 text-slate-800 font-bold">${p.descricao}</td>
            <td class="p-3 text-center">
                <input type="number" min="1" value="${p.quantidade}" class="w-20 text-center border border-slate-300 rounded px-2 py-1" onchange="remProductosCaixa[${i}].quantidade = parseInt(this.value); atualizarInterfaceRemision();">
            </td>
            <td class="p-3 text-center">
                <button onclick="remProductosCaixa.splice(${i}, 1); atualizarInterfaceRemision();" class="text-red-500 hover:text-red-700 font-bold">✕</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ==================== CATÁLOGO ====================
function abrirCatalogo(origem) {
    contextoCatalogo = origem;
    document.getElementById('modal-catalogo-pdv').classList.remove('hidden');
    document.getElementById('modal-catalogo-pdv').classList.add('flex');
    carregarCatalogoPDV();
}

function fecharCatalogoPDV() {
    document.getElementById('modal-catalogo-pdv').classList.add('hidden');
    document.getElementById('modal-catalogo-pdv').classList.remove('flex');
}

async function carregarCatalogoPDV() {
    try {
        // Si ya tenemos los productos globales, usarlos
        if (productosGlobais && productosGlobais.length > 0) {
            popularFiltrosCatalogo(productosGlobais);
            renderizarCatalogoPDV(productosGlobais);
            return;
        }
        // Si no, cargar desde el servidor
        const res = await fetch('/listar-produtos', {headers: getSaaSHeaders()});
        const d = await res.json();
        const ordenada = d.sort((a, b) => a.descricao.localeCompare(b.descricao));
        productosGlobais = ordenada;
        popularFiltrosCatalogo(ordenada);
        renderizarCatalogoPDV(ordenada);
    } catch(e) {
        console.error(e);
        document.getElementById('tabela-catalogo-pdv').innerHTML = '<tr><td colspan="4" class="p-6 text-center text-red-400">Error al cargar productos</td></tr>';
    }
}

function popularFiltrosCatalogo(lista) {
    // Extraer categorias únicas
    const categorias = [...new Set(lista.map(p => p.categoria).filter(c => c && c.trim() !== ''))];
    categorias.sort();
    const selectCat = document.getElementById('catalogo-categoria');
    if (selectCat) {
        // Mantener la opción "Todas las Categorías" ya existente
        while (selectCat.options.length > 1) selectCat.remove(1);
        categorias.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            selectCat.appendChild(opt);
        });
    }
    // Extraer proveedores únicos
    const proveedores = [...new Set(lista.map(p => p.proveedor || p.nome_proveedor || '').filter(p => p && p.trim() !== ''))];
    proveedores.sort();
    const selectProv = document.getElementById('catalogo-proveedor');
    if (selectProv) {
        while (selectProv.options.length > 1) selectProv.remove(1);
        proveedores.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p;
            selectProv.appendChild(opt);
        });
    }
}

function renderizarCatalogoPDV(lista) {
    const tbody = document.getElementById('tabela-catalogo-pdv');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (lista.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-slate-400">No hay productos registrados</td></tr>';
        return;
    }
    lista.forEach(p => {
        const precio = p.preco_venda || p.preco || 0;
        const stock = p.quantidade || 0;
        tbody.innerHTML += `<tr class="border-b border-slate-200 hover:bg-slate-50">
            <td class="p-3 text-slate-800 font-bold">${p.descricao}</td>
            <td class="p-3 text-right font-bold text-green-600">Gs. ${precio.toLocaleString('es-PY')}</td>
            <td class="p-3 text-center font-bold ${stock > 0 ? 'text-blue-600' : 'text-red-600'}">${stock}</td>
            <td class="p-3 text-center">
                <button onclick="seleccionarProductoCatalogo('${p.codigo_barras}')" class="bg-brand-accent hover:bg-brand-accentHover text-white px-4 py-2 rounded-lg font-bold text-sm shadow-sm transition">Agregar</button>
            </td>
        </tr>`;
    });
}

function filtrarCatalogoPDV() {
    const term = document.getElementById('catalogo-busca').value.toLowerCase();
    const cat = document.getElementById('catalogo-categoria').value;
    const prov = document.getElementById('catalogo-proveedor').value;
    const lista = productosGlobais || [];
    const filtrada = lista.filter(p => {
        // Filtro por texto (nombre o código)
        const textoOk = term === '' || 
            p.descricao.toLowerCase().includes(term) || 
            (p.codigo_barras && p.codigo_barras.toLowerCase().includes(term));
        // Filtro por categoría (si se seleccionó una)
        const catOk = cat === '' || p.categoria === cat;
        // Filtro por proveedor (si se seleccionó uno)
        const provOk = prov === '' || p.proveedor === prov || p.nome_proveedor === prov;
        return textoOk && catOk && provOk;
    });
    renderizarCatalogoPDV(filtrada);
}

function seleccionarProductoEntrada(producto) {
    const q = prompt(`Cant de ${producto.descricao}:`);
    if (!q) return;
    const cost = prompt(`Costo:`, producto.preco_custo);
    if (!cost) return;
    itensEntrada.push({
        codigo_barras: producto.codigo_barras,
        descricao: producto.descricao,
        quantidade: parseInt(q),
        custo_unitario: parseFloat(cost)
    });
    atualizarInterfaceEntrada();
}

function agregarProductoEntrada(codigo) {
    const p = productosGlobais.find(x => x.codigo_barras === codigo);
    if (!p) return;
    const q = prompt(`Cant de ${p.descricao}:`);
    if (!q) return;
    const cost = prompt(`Costo:`, p.preco_custo);
    if (!cost) return;
    itensEntrada.push({
        codigo_barras: codigo,
        descricao: p.descricao,
        quantidade: parseInt(q),
        custo_unitario: parseFloat(cost)
    });
    atualizarInterfaceEntrada();
    document.getElementById('entrada-scanner').value = '';
}

function seleccionarProductoCatalogo(codigo) {
    const producto = productosGlobais.find(p => p.codigo_barras === codigo);
    if (!producto) return;
    if (contextoCatalogo === 'entrada') {
        seleccionarProductoEntrada(producto);
    } else if (contextoCatalogo === 'remision') {
        seleccionarProdutoRemision(producto);
    } else if (contextoCatalogo === 'autofactura') {
        seleccionarProdutoAuto(producto);
    } else {
        // Por defecto PDV
        seleccionarProductoPOS(producto);
    }
    fecharCatalogoPDV();
}

async function carregarProveedores() { try { const res=await fetch('/listar-proveedores', {headers:getSaaSHeaders()}); const d=await res.json(); const ordenada = d.sort((a, b) => a.nome.localeCompare(b.nome)); const tb=document.getElementById('tabela-proveedores'); if(tb) { tb.innerHTML=''; ordenada.forEach(p=>{ tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${p.nome}</td><td class="p-4 text-gray-400">${p.telefone||''}</td><td class="p-4">${p.endereco||''}</td><td class="p-4"><button onclick="abrirModalEditarProveedor(${p.id},'${p.nome}','${p.ruc}','${p.telefone}','${p.email}','${p.endereco}')" class="text-blue-400 mr-2">✏️</button><button onclick="deletarProveedor(${p.id})" class="text-red-400">🗑️</button></td></tr>`; }); } const sp=document.getElementById('novo-prov'); if(sp) { sp.innerHTML='<option value="">Ninguno</option>'; ordenada.forEach(p=>{ sp.innerHTML+=`<option value="${p.nome}">${p.nome}</option>`; }); } const sep=document.getElementById('entrada-prov'); if(sep) { sep.innerHTML='<option value="">Seleccionar Proveedor</option>'; ordenada.forEach(p=>{ sep.innerHTML+=`<option value="${p.id}">${p.nome}</option>`; }); } const spp=document.getElementById('stocktake-proveedor'); if(spp) { spp.innerHTML='<option value="">Todos los proveedores</option>'; ordenada.forEach(p=>{ spp.innerHTML+=`<option value="${p.nome}">${p.nome}</option>`; }); } } catch(e){} }
function abrirModalEditarProveedor(id, n, r, t, e, end) { document.getElementById('prov-id').value=id; document.getElementById('prov-nome').value=n; document.getElementById('prov-ruc').value=r!=='null'?r:''; document.getElementById('prov-tel').value=t!=='null'?t:''; document.getElementById('prov-email').value=e!=='null'?e:''; document.getElementById('prov-endereco').value=end!=='null'?end:''; document.getElementById('form-novo-proveedor').classList.remove('hidden'); }
async function salvarProveedor() { const id=document.getElementById('prov-id').value; const pay={nome:document.getElementById('prov-nome').value, ruc:document.getElementById('prov-ruc').value, telefone:document.getElementById('prov-tel').value, email:document.getElementById('prov-email').value, endereco:document.getElementById('prov-endereco').value}; const url=id?`/editar-proveedor/${id}`:'/cadastrar-proveedor'; const m=id?'PUT':'POST'; try { await fetch(url,{method:m,headers:getSaaSHeaders(),body:JSON.stringify(pay)}); document.getElementById('form-novo-proveedor').classList.add('hidden'); document.getElementById('prov-id').value = ''; document.getElementById('prov-nome').value = ''; document.getElementById('prov-ruc').value = ''; document.getElementById('prov-tel').value = ''; document.getElementById('prov-email').value = ''; document.getElementById('prov-endereco').value = ''; carregarProveedores(); } catch(e){} } async function deletarProveedor(id) { if(confirm("Del?")) { await fetch(`/deletar-proveedor/${id}`,{method:'DELETE',headers:getSaaSHeaders()}); carregarProveedores(); } }

function buscarProdutoEntrada(e) {
    if(e.key === 'Enter') {
        e.preventDefault();
        const codigo = document.getElementById('entrada-scanner').value;
        agregarProductoEntrada(codigo);
    }
}
function atualizarInterfaceEntrada() { const tb=document.getElementById('tabela-entrada-itens'); tb.innerHTML=''; let t=0; itensEntrada.forEach((i,idx)=>{ const st=i.quantidade*i.custo_unitario; t+=st; tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-3 text-white">${i.descricao}</td><td class="p-3 text-center text-white">${i.quantidade}</td><td class="p-3 text-right">Gs. ${i.custo_unitario.toLocaleString('es-PY')}</td><td class="p-3 text-right font-bold text-blue-400">Gs. ${st.toLocaleString('es-PY')}</td><td class="p-3 text-center"><button onclick="itensEntrada.splice(${idx},1);atualizarInterfaceEntrada();" class="text-red-400">✕</button></td></tr>`; }); document.getElementById('entrada-total-tela').innerText=t.toLocaleString('es-PY'); }
async function salvarEntradaFactura() { if(itensEntrada.length===0) return; const p=document.getElementById('entrada-prov').value; const n=document.getElementById('entrada-nro').value; const d=document.getElementById('entrada-data').value; if(!p||!n) return showToast("Falta info", "error"); try { await fetch('/salvar-entrada',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({proveedor_id:parseInt(p), numero_factura:n, data_emissao:d, itens:itensEntrada})}); showToast("✅ Factura Guardada"); itensEntrada=[]; atualizarInterfaceEntrada(); document.getElementById('entrada-nro').value=''; carregarEstoque(); } catch(e){} }

function filtrarMerma() { const inp = document.getElementById('merma-cod').value.toLowerCase(); const drop = document.getElementById('merma-dropdown'); drop.innerHTML = ''; if (inp.length < 2) { drop.classList.add('hidden'); return; } const res = productosGlobais.filter(p => p.descricao.toLowerCase().includes(inp) || p.codigo_barras.toLowerCase().includes(inp)).slice(0, 10); if (res.length > 0) { drop.classList.remove('hidden'); res.forEach(p => { const div = document.createElement('div'); div.className = 'p-3 border-b border-slate-600 hover:bg-slate-600 cursor-pointer text-white'; div.innerHTML = p.descricao; div.onclick = () => { drop.classList.add('hidden'); document.getElementById('merma-cod').value = p.codigo_barras; document.getElementById('merma-atual').value = p.quantidade; document.getElementById('merma-add').focus(); }; drop.appendChild(div); }); } else { drop.classList.add('hidden'); } }
function buscarParaMerma(e) { if(e.key === 'Enter') { e.preventDefault(); const c = document.getElementById('merma-cod').value.trim(); const p = productosGlobais.find(x => x.codigo_barras === c); if(p) { document.getElementById('merma-dropdown').classList.add('hidden'); document.getElementById('merma-cod').value = p.codigo_barras; document.getElementById('merma-atual').value = p.quantidade; document.getElementById('merma-add').focus(); } } }
async function salvarMerma() { const c = document.getElementById('merma-cod').value; const q = parseInt(document.getElementById('merma-add').value); const m = document.getElementById('merma-motivo').value; if(!c || !q || q<=0) return; try { const res = await fetch('/registrar-merma', { method:'POST', headers:getSaaSHeaders(), body:JSON.stringify({codigo_barras:c, quantidade:q, motivo:m}) }); if(res.ok) { showToast("✅ Baja registrada."); document.getElementById('merma-cod').value=''; document.getElementById('merma-atual').value=''; document.getElementById('merma-add').value=''; carregarMermas(); carregarEstoque(); } else { const err = await res.json(); showToast("❌ " + err.detail, "error"); } } catch(e){} }
async function carregarMermas() { try { const res = await fetch('/listar-mermas', {headers:getSaaSHeaders()}); const d = await res.json(); const tb = document.getElementById('tabela-mermas'); tb.innerHTML = ''; d.forEach(m => { const loss = m.quantidade * m.custo; tb.innerHTML += `<tr class="border-b border-slate-700 hover:bg-slate-700/30"><td class="p-3 text-gray-400 text-xs">${m.data}</td><td class="p-3 text-white font-bold">${m.descricao}</td><td class="p-3 text-center text-red-400 font-bold">${m.quantidade}</td><td class="p-3 text-gray-400">${m.motivo}</td><td class="p-3 text-right text-red-400 font-bold">Gs. ${loss.toLocaleString('es-PY')}</td></tr>`; }); } catch(e){} }

function filtrarNC() { const input = document.getElementById('nc-scanner').value.toLowerCase(); const dropdown = document.getElementById('nc-dropdown'); dropdown.innerHTML = ''; if (input.length < 2) { dropdown.classList.add('hidden'); return; } const resultados = productosGlobais.filter(p => p.descricao.toLowerCase().includes(input) || p.codigo_barras.toLowerCase().includes(input)).slice(0, 10); if (resultados.length > 0) { dropdown.classList.remove('hidden'); resultados.forEach(p => { const div = document.createElement('div'); div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white'; div.innerHTML = `<span>${p.descricao}</span><span class="text-purple-400 font-bold">Gs. ${p.preco_venda.toLocaleString('es-PY')}</span>`; div.onclick = () => seleccionarProdutoNC(p); dropdown.appendChild(div); }); } else { dropdown.classList.add('hidden'); } }
function seleccionarProdutoNC(prod) { document.getElementById('nc-dropdown').classList.add('hidden'); document.getElementById('nc-scanner').value = ''; const idx = ncProductosCaixa.findIndex(p => p.codigo_barras === prod.codigo_barras); if (idx !== -1) ncProductosCaixa[idx].quantidade += 1; else ncProductosCaixa.push({ codigo_barras: prod.codigo_barras, descricao: prod.descricao, quantidade: 1, preco_unitario: Number(prod.preco_venda) }); atualizarInterfaceNC(); }
function verificarScannerNC(e) { if(e && e.key === 'Enter') { e.preventDefault(); const codigo = document.getElementById('nc-scanner').value.trim(); document.getElementById('nc-scanner').value = ''; document.getElementById('nc-dropdown').classList.add('hidden'); const pGlobal = productosGlobais.find(p=>p.codigo_barras === codigo); if(pGlobal) seleccionarProdutoNC(pGlobal); } }
function atualizarInterfaceNC() { const tbody = document.getElementById('nc-lista-produtos'); tbody.innerHTML = ''; let sub = 0; ncProductosCaixa.forEach((p, i) => { const st = p.quantidade * p.preco_unitario; sub += st; tbody.innerHTML += `<div class="bg-slate-700/50 p-3 rounded-lg flex justify-between items-center mb-2"><div><span class="text-black block" style="color: #000 !important;">${p.descricao}</span></div><div class="flex items-center gap-3"><span class="text-black font-bold" style="color: #000 !important;">${p.quantidade} unid.</span><span class="font-bold text-purple-400 w-24 text-right">Gs. ${st.toLocaleString('es-PY')}</span><button onclick="ncProductosCaixa.splice(${i}, 1); atualizarInterfaceNC();" class="text-red-400 font-bold bg-red-900/20 px-2 rounded">✕</button></div></div>`; }); totalNCTela = sub; document.getElementById('nc-valor-total-tela').innerText = sub.toLocaleString('es-PY'); }
async function emitirNotaCredito() { 
    const cdcRef = document.getElementById('nc-cdc').value.trim(); 
    const cl = document.getElementById('nc-cliente').value.trim(); 
    if(ncProductosCaixa.length === 0 || !cdcRef || !cl) return showToast("Complete todo.", "warning"); 
    const btn = document.getElementById('btn-emitir-nc'); 
    btn.disabled = true; 
    const payload = { 
        ruc_emissor: document.getElementById('ruc').value, 
        nome_cliente: cl, 
        valor_total: totalNCTela, 
        itens: ncProductosCaixa, 
        cdc_referencia: cdcRef, 
        metodo_pago: "Devolucion" 
    }; 
    try { 
        const res = await fetch('/emitir-nota', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(payload) }); 
        const dados = await res.json(); 
        if (dados.demo_mode) {
            alert(dados.mensaje);
            ncProductosCaixa = [];
            atualizarInterfaceNC();
            carregarEstoque();
            return;
        }
        document.getElementById('nc-resultado').classList.remove('hidden'); 
        document.getElementById('btn-nc-pdf').href = dados.link_pdf; 
        btn.classList.add('hidden'); 
        ncProductosCaixa = []; 
        atualizarInterfaceNC(); 
        carregarEstoque(); 
    } catch(e) {} finally { btn.disabled = false; } 
}
function novaNC() { document.getElementById('nc-resultado').classList.add('hidden'); document.getElementById('btn-emitir-nc').classList.remove('hidden'); document.getElementById('nc-cdc').value = ''; document.getElementById('nc-cliente').value = ''; document.getElementById('nc-scanner').focus(); }

function filtrarRemision() {
    const input = document.getElementById('rem-scanner').value.toLowerCase();
    const dropdown = document.getElementById('rem-dropdown');
    dropdown.innerHTML = '';
    if (input.length < 2) {
        dropdown.classList.add('hidden');
        return;
    }
    const resultados = productosGlobais.filter(p =>
        p.descricao.toLowerCase().includes(input) ||
        p.codigo_barras.toLowerCase().includes(input)
    ).slice(0, 10);
    if (resultados.length > 0) {
        dropdown.classList.remove('hidden');
        resultados.forEach(p => {
            const div = document.createElement('div');
            div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white';
            div.innerHTML = `<span>${p.descricao}</span><span class="text-yellow-400 font-bold">Stock: ${p.quantidade}</span>`;
            div.onclick = () => seleccionarProdutoRemision(p);
            dropdown.appendChild(div);
        });
    } else {
        dropdown.classList.add('hidden');
    }
}

function seleccionarProdutoRemision(prod) {
    document.getElementById('rem-dropdown').classList.add('hidden');
    document.getElementById('rem-scanner').value = '';
    const idx = remProductosCaixa.findIndex(p => p.codigo_barras === prod.codigo_barras);
    if (idx !== -1) {
        remProductosCaixa[idx].quantidade += 1;
    } else {
        remProductosCaixa.push({
            codigo_barras: prod.codigo_barras,
            descricao: prod.descricao,
            quantidade: 1
        });
    }
    atualizarInterfaceRemision();
}

function verificarScannerRemision(e) {
    if (e && e.key === 'Enter') {
        e.preventDefault();
        const codigo = document.getElementById('rem-scanner').value.trim();
        document.getElementById('rem-scanner').value = '';
        document.getElementById('rem-dropdown').classList.add('hidden');
        const pGlobal = productosGlobais.find(p => p.codigo_barras === codigo);
        if (pGlobal) seleccionarProdutoRemision(pGlobal);
    }
}

function emitirRemision() {
    if (remProductosCaixa.length === 0) return showToast("Agregue productos a la remisión.", "warning");
    showToast("Función de remisión en desarrollo", "info");
    // TODO: implementar llamada al backend
}

function novaRemision() {
    document.getElementById('rem-resultado').classList.add('hidden');
    document.getElementById('btn-emitir-rem').classList.remove('hidden');
    remProductosCaixa = [];
    atualizarInterfaceRemision();
}

function abrirModalTutorialMP() { document.getElementById('modal-tutorial-mp').classList.remove('hidden'); document.getElementById('modal-tutorial-mp').classList.add('flex'); }
function fecharModalTutorialMP() { document.getElementById('modal-tutorial-mp').classList.add('hidden'); document.getElementById('modal-tutorial-mp').classList.remove('flex'); }
function adicionarItemLibreAuto() { const desc = prompt("Descripción del Servicio/Gasto:"); if(!desc) return; const qtdStr = prompt("Cantidad:", "1"); if(!qtdStr) return; const precoStr = prompt("Precio Unitario (Gs):"); if(!precoStr) return; autoProductosCaixa.push({ codigo_barras: "", descricao: desc, quantidade: parseInt(qtdStr) || 1, preco_unitario: parseFloat(precoStr) || 0 }); atualizarInterfaceAuto(); }
function filtrarAuto() { const input = document.getElementById('auto-scanner').value.toLowerCase(); const dropdown = document.getElementById('auto-dropdown'); dropdown.innerHTML = ''; if (input.length < 2) { dropdown.classList.add('hidden'); return; } const resultados = productosGlobais.filter(p => p.descricao.toLowerCase().includes(input) || p.codigo_barras.toLowerCase().includes(input)).slice(0, 10); if (resultados.length > 0) { dropdown.classList.remove('hidden'); resultados.forEach(p => { const div = document.createElement('div'); div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white'; div.innerHTML = `<span>${p.descricao}</span><span class="text-orange-400 font-bold">Stock: ${p.quantidade}</span>`; div.onclick = () => seleccionarProdutoAuto(p); dropdown.appendChild(div); }); } else { dropdown.classList.add('hidden'); } }
function seleccionarProdutoAuto(prod) { document.getElementById('auto-dropdown').classList.add('hidden'); document.getElementById('auto-scanner').value = ''; const qStr = prompt(`Cantidad comprada de:\n${prod.descricao}`); if(!qStr) return; const q = parseInt(qStr); if(isNaN(q) || q<=0) return; const cStr = prompt(`Costo Unitario de compra (Gs):`, prod.preco_custo); if(!cStr) return; const c = parseFloat(cStr); if(isNaN(c) || c<0) return; autoProductosCaixa.push({ codigo_barras: prod.codigo_barras, descricao: prod.descricao, quantidade: q, preco_unitario: c }); atualizarInterfaceAuto(); }
function verificarScannerAuto(e) { if(e && e.key === 'Enter') { e.preventDefault(); const codigo = document.getElementById('auto-scanner').value.trim(); document.getElementById('auto-scanner').value = ''; document.getElementById('auto-dropdown').classList.add('hidden'); const pGlobal = productosGlobais.find(p=>p.codigo_barras === codigo); if(pGlobal) seleccionarProdutoAuto(pGlobal); else showToast("No en inventario. Use 'Añadir Servicio Manual'.", "warning"); } }
function atualizarInterfaceAuto() { const tbody = document.getElementById('tabela-auto-itens'); tbody.innerHTML = ''; let sub = 0; if(autoProductosCaixa.length === 0) { tbody.innerHTML = '<tr><td colspan="5" class="p-6 text-center text-gray-500">Agregue productos o servicios.</td></tr>'; document.getElementById('auto-total-tela').innerText = "0"; return; } autoProductosCaixa.forEach((p, i) => { const st = p.quantidade * p.preco_unitario; sub += st; tbody.innerHTML += `<tr class="border-b border-slate-700 hover:bg-slate-700/30"><td class="p-3 text-white font-bold">${p.descricao} ${p.codigo_barras?'<span class="text-[10px] text-gray-500 font-mono block">'+p.codigo_barras+'</span>':''}</td><td class="p-3 text-center text-white">${p.quantidade}</td><td class="p-3 text-right text-gray-300">Gs. ${p.preco_unitario.toLocaleString('es-PY')}</td><td class="p-3 text-right font-bold text-orange-400">Gs. ${st.toLocaleString('es-PY')}</td><td class="p-3 text-center"><button onclick="autoProductosCaixa.splice(${i}, 1); atualizarInterfaceAuto();" class="text-red-400 font-bold bg-red-900/20 px-2 py-1 rounded">✕</button></td></tr>`; }); totalAutoTela = sub; document.getElementById('auto-total-tela').innerText = sub.toLocaleString('es-PY'); }
async function emitirAutofactura() { const nom = document.getElementById('auto-nome').value.trim(); const ced = document.getElementById('auto-cedula').value.trim(); const end = document.getElementById('auto-endereco').value.trim(); const moverStock = document.getElementById('auto-mover-stock').checked; if(autoProductosCaixa.length === 0 || !nom || !ced || !end) return showToast("Complete todos los datos del vendedor y agregue ítems.", "warning"); const btn = document.getElementById('btn-emitir-auto'); btn.disabled = true; btn.innerHTML = '⏳ Generando Autofactura...'; const payload = { nome_vendedor: nom, cedula_vendedor: ced, endereco_vendedor: end, mover_stock: moverStock, itens: autoProductosCaixa }; try { const res = await fetch('/emitir-autofactura', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(payload) }); if(!res.ok) throw new Error((await res.json()).detail); const dados = await res.json(); document.getElementById('auto-resultado').classList.remove('hidden'); document.getElementById('btn-auto-pdf').href = dados.link_pdf; btn.classList.add('hidden'); autoProductosCaixa = []; atualizarInterfaceAuto(); carregarAutofacturas(); carregarEstoque(); showToast("✅ Autofactura Emitida."); } catch(e) { showToast("❌ Error: " + e.message, "error"); } finally { btn.disabled = false; btn.innerHTML = '🧾 Emitir Autofactura SIFEN'; } }
function novaAutofactura() { document.getElementById('auto-resultado').classList.add('hidden'); document.getElementById('btn-emitir-auto').classList.remove('hidden'); ['auto-nome','auto-cedula','auto-endereco'].forEach(id=>document.getElementById(id).value=''); document.getElementById('auto-scanner').focus(); }
async function carregarAutofacturas() { try { const res = await fetch('/listar-autofacturas', {headers:getSaaSHeaders()}); const d = await res.json(); const tb = document.getElementById('tabela-hist-auto'); tb.innerHTML = ''; d.forEach(r => { tb.innerHTML += `<tr class="border-b border-slate-700 hover:bg-slate-700/30"><td class="p-3"><div class="font-bold text-white text-xs">${r.data}</div><div class="text-[10px] text-gray-500 font-mono">${r.cdc.substring(0,25)}...</div></td><td class="p-3 text-white font-bold">${r.vendedor}</td><td class="p-3 text-right font-bold text-orange-400">Gs. ${r.valor.toLocaleString('es-PY')}</td><td class="p-3 text-center"><a href="${r.link_pdf}" target="_blank" class="bg-slate-700 text-white px-3 py-1 rounded text-xs font-bold border border-slate-600">PDF</a></td></tr>`; }); } catch(e){} }

// FUNÇÕES DA TELA DO PIX
function abrirModalPix(valorReaisEstimado) {
    document.getElementById('modal-pix').classList.remove('hidden');
    document.getElementById('modal-pix').classList.add('flex');
    document.getElementById('pix-valor-reais').innerText = valorReaisEstimado.toFixed(2).replace('.', ',');
    document.getElementById('pix-qrcode-img').classList.add('hidden');
    document.getElementById('pix-loading').classList.remove('hidden');
}

function fecharModalPix() {
    clearInterval(radarPix);
    document.getElementById('modal-pix').classList.add('hidden');
    document.getElementById('modal-pix').classList.remove('flex');
}

function copiarCodigoPix() {
    if (pixCopiaEColaAtual) {
        navigator.clipboard.writeText(pixCopiaEColaAtual)
            .then(() => showToast("✅ Código copiado con éxito"))
            .catch(() => showToast("❌ Error al copiar"));
    }
}

// FUNÇÃO QUE CHAMA O PYTHON
async function gerarPixNaTela(valorGuaranis) {
    try {
        abrirModalPix(valorGuaranis / 1450); 

        const resposta = await fetch('/gerar-pix', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Empresa-ID': empresaAtualId.toString()
            },
            body: JSON.stringify({ valor_guaranis: parseFloat(valorGuaranis) })
        });

        const dados = await resposta.json();

        if (resposta.ok && dados.sucesso) {
            document.getElementById('pix-loading').classList.add('hidden');
            
            const imgQrCode = document.getElementById('pix-qrcode-img');
            imgQrCode.src = "data:image/jpeg;base64," + dados.qr_code_base64;
            imgQrCode.classList.remove('hidden');

            document.getElementById('pix-valor-reais').innerText = dados.valor_reais.toFixed(2).replace('.', ',');
            pixCopiaEColaAtual = dados.copia_cola;
            
            iniciarRadarPix(dados.id_pagamento_mp);

        } else {
            fecharModalPix();
            showToast("❌ " + (dados.detail || "Error al generar PIX"));
        }
    } catch (erro) {
        fecharModalPix();
        console.error(erro);
        showToast("❌ Error de conexión");
    }
}

// ==========================================
// FUNÇÕES DO SUPER ADMIN (COBRANÇA SIPAP)
// ==========================================

async function gerarFaturaSaaS(empresaId) {
    if (!confirm("¿Generar factura de mensualidad para esta empresa? (Plazo: 5 días)")) return;
    
    try {
        const res = await fetch(`/super-admin/gerar-fatura/${empresaId}`, { method: 'POST' });
        const dados = await res.json();
        
        if (res.ok && dados.sucesso) {
            showToast("✅ " + dados.detail);
            carregarFaturasSaaS(); // Atualiza a tabela na hora
        } else {
            showToast("❌ " + (dados.detail || "Error al generar"), "error");
        }
    } catch(e) {
        showToast("❌ Error de conexión", "error");
    }
}

async function carregarFaturasSaaS() {
    try {
        const res = await fetch('/super-admin/faturas');
        if (res.ok) {
            const faturas = await res.json();
            const tbody = document.getElementById('tabela-faturas-saas');
            if (!tbody) return; 
            
            tbody.innerHTML = '';
            faturas.forEach(f => {
                // Como o Python devolve uma lista (tupla), pegamos pelas posições [0, 1, 2...]
                const id = f.id || f[0];
                const nome = f.nome_empresa || f[1];
                const valor = f.valor || f[2];
                const venc = (f.data_vencimento || f[3]).split(' ')[0]; // Pega só a data, sem a hora
                const status = f.status || f[4];
                
                let corStatus = status === 'Pago' ? 'text-green-400 font-bold' : 'text-yellow-400 font-bold animate-pulse';
                let btnAprovar = status === 'Pendente' 
                    ? `<button onclick="aprovarPagamentoSaaS(${id})" class="bg-green-600 hover:bg-green-500 text-white px-3 py-1 rounded text-xs font-bold transition shadow-lg">Aprobar Pago</button>` 
                    : `<span class="text-gray-500 text-xs font-bold border border-gray-600 px-2 py-1 rounded">✅ Aprobado</span>`;

                tbody.innerHTML += `
                    <tr class="border-b border-slate-700 hover:bg-slate-700/30">
                        <td class="p-3 text-white font-bold">${nome}</td>
                        <td class="p-3 text-orange-400 font-bold">Gs. ${Number(valor).toLocaleString('es-PY')}</td>
                        <td class="p-3 text-gray-400 text-sm">${venc}</td>
                        <td class="p-3 ${corStatus}">${status}</td>
                        <td class="p-3 text-center">${btnAprovar}</td>
                    </tr>
                `;
            });
        }
    } catch(e) {}
}

async function aprovarPagamentoSaaS(faturaId) {
    if (!confirm("¿Confirmar que recibiste la transferencia SIPAP en tu cuenta bancaria?")) return;
    
    try {
        const res = await fetch(`/super-admin/faturas/${faturaId}/pagar`, { method: 'PUT' });
        if (res.ok) {
            showToast("✅ Pago Aprobado y registrado!");
            carregarFaturasSaaS(); // Atualiza a tabela na hora
        } else {
            showToast("❌ Error al aprobar", "error");
        }
    } catch(e) {
        showToast("❌ Error de red", "error");
    }
}

// ==========================================
// GESTIÓN DE EQUIPO (por plan)
// ==========================================

function actualizarUIEquipe() {
    // Configurar dropdown de roles segun plan de forma direta
    const selectRol = document.getElementById('equipo-rol');
    if (selectRol) {
        if (planoAtivo.includes('Crecimiento')) {
            selectRol.innerHTML = '<option value="cajero">Cajero</option>';
            selectRol.disabled = true;
            selectRol.title = "Plan Crecimiento: solo puede agregar usuarios con rol Cajero.";
        } else {
            // Planos VIP e outros (habilita as duas opções)
            selectRol.innerHTML = '<option value="cajero">Cajero</option><option value="gerente">Gerente</option>';
            selectRol.disabled = false;
            selectRol.title = "";
            selectRol.classList.remove('bg-slate-100', 'cursor-not-allowed');
        }
    }

    // Cargar usuarios existentes y actualizar estado del boton
    cargarUsuariosEquipo();
    actualizarEstadoBotonAgregar();
}
    

function iniciarConfig() {
    // Actualizar UI de gestión de equipo basado en el plan
    actualizarUIEquipe();
    // Activar pestaña Empresa por defecto
    cambiarTabConfig('empresa');
}

async function cargarUsuariosEquipo() {
    const tbody = document.getElementById('tabela-equipo');
    if (!tbody) return;
    
    try {
        const res = await fetch('/equipo/listar', { headers: getSaaSHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        usuariosEquipo = await res.json();
        
        if (usuariosEquipo.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="p-6 text-center text-slate-400">No hay usuarios registrados aún.</td></tr>';
            actualizarEstadoBotonAgregar();
            return;
        }
        
        let html = '';
        usuariosEquipo.forEach((u, idx) => {
            let rolLabel = u.rol === 'cajero' ? 'Cajero' : 'Gerente';
            let estadoLabel = u.ativo ? '<span class="text-green-500">Activo</span>' : '<span class="text-red-500">Inactivo</span>';
            html += `
                <tr class="border-b border-slate-100 hover:bg-slate-50">
                    <td class="p-3 text-slate-800 font-bold">${u.nome}</td>
                    <td class="p-3">${rolLabel}</td>
                    <td class="p-3">${u.email}</td>
                    <td class="p-3">${estadoLabel}</td>
                    <td class="p-3 text-right">
                        <button onclick="eliminarUsuarioEquipo(${u.id})" class="text-red-500 hover:text-red-700 font-bold">🗑️</button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
        actualizarEstadoBotonAgregar();
    } catch (error) {
        console.error('Error cargando equipo:', error);
        // Fallback a localStorage solo para compatibilidad
        if (usuariosEquipo.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="p-6 text-center text-slate-400">No hay usuarios registrados aún.</td></tr>';
        }
        actualizarEstadoBotonAgregar();
    }
}

async function agregarUsuarioEquipo() {
    const nombre = document.getElementById('equipo-nombre').value.trim();
    const rol = document.getElementById('equipo-rol').value;
    const email = document.getElementById('equipo-email').value.trim();
    const password = document.getElementById('equipo-password').value.trim();

    // Força a tradução do cargo para o formato aceito pelo banco de dados
    let rolFormatado = rol.toLowerCase();
    if (rolFormatado === 'manager') rolFormatado = 'gerente';
    if (rolFormatado === 'cashier') rolFormatado = 'cajero';
    
    if (!nombre || !rol || !email || !password) {
        showToast("Complete todos los campos.", "warning");
        return;
    }
    
    // Restricción de límite para Plan Crecimiento (Pro) - validación frontend
    if (planoAtivo.includes('Crecimiento') && rolFormatado === 'cajero') {
        const cajerosActuales = usuariosEquipo.filter(u => u.rol === 'cajero' && u.activo).length;
        if (cajerosActuales >= 1) {
            showToast("Limite del Plan Crecimiento alcanzado. Mejore al Plan VIP para añadir usuarios ilimitados.");
            return;
        }
    }
    
    try {
        const res = await fetch('/equipo/adicionar', {
            method: 'POST',
            headers: { ...getSaaSHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome: nombre, email, senha: password, rol: rolFormatado })
        });
        
        if (!res.ok) {
            let errorMsg = 'Error al agregar usuario';
            const textoResposta = await res.text(); // Lemos o pacote do servidor apenas UMA vez
            
            try {
                // Tentamos ver se o texto é um dicionário JSON
                const errorData = JSON.parse(textoResposta);
                errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData);
            } catch {
                // Se não for um JSON, usamos o texto puro mesmo
                errorMsg = textoResposta || errorMsg;
            }
            
            throw new Error(errorMsg);
        }
        
        // Limpiar campos
        document.getElementById('equipo-nombre').value = '';
        document.getElementById('equipo-email').value = '';
        document.getElementById('equipo-password').value = '';
        
        // Actualizar tabla
        await cargarUsuariosEquipo();
        showToast("Usuario agregado correctamente.");
   } catch (error) {
            console.error('Error agregando usuario:', error);
            let mensaje = "Error al agregar usuario";
            if (typeof error.message === 'string') mensaje = error.message;
            else if (error.detail) mensaje = error.detail;
            else if (error.error) mensaje = JSON.stringify(error.error);
            
            showToast(mensaje, "error");
        }
}

async function eliminarUsuarioEquipo(funcionarioId) {
    if (!confirm("¿Eliminar este usuario?")) return;
    
    try {
        const res = await fetch(`/equipo/remover/${funcionarioId}`, {
            method: 'DELETE',
            headers: getSaaSHeaders()
        });
        
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Error al eliminar usuario');
        }
        
        await cargarUsuariosEquipo();
        showToast("Usuario eliminado.");
    } catch (error) {
        console.error('Error eliminando usuario:', error);
        showToast(error.message || "Error al eliminar usuario", "error");
    }
}

function actualizarEstadoBotonAgregar() {
    const boton = document.querySelector('button[onclick="agregarUsuarioEquipo()"]');
    if (!boton) return;
    
    if (planoAtivo.includes('Crecimiento')) {
        const cajerosActuales = usuariosEquipo.filter(u => u.rol === 'cajero').length;
        if (cajerosActuales >= 1) {
            boton.disabled = true;
            boton.classList.add('opacity-50', 'cursor-not-allowed');
            boton.title = "Límite alcanzado. Mejore al Plan VIP para añadir más usuarios.";
        } else {
            boton.disabled = false;
            boton.classList.remove('opacity-50', 'cursor-not-allowed');
            boton.title = "";
        }
    } else if (planoAtivo.includes('VIP')) {
        boton.disabled = false;
        boton.classList.remove('opacity-50', 'cursor-not-allowed');
        boton.title = "";
    }
}

async function alterarCredenciaisAdmin() {
    const senhaAtual = document.getElementById('seguridad-senha-atual').value.trim();
    const novoLogin = document.getElementById('seguridad-novo-login').value.trim();
    const novaSenha = document.getElementById('seguridad-nova-senha').value.trim();
    const confirmarSenha = document.getElementById('seguridad-confirmar-senha').value.trim();
    
    if (!senhaAtual || !novoLogin || !novaSenha || !confirmarSenha) {
        showToast("Complete todos los campos del formulario.", "error");
        return;
    }
    if (novaSenha.length < 6) {
        showToast("La nueva contraseña debe tener al menos 6 caracteres.", "error");
        return;
    }
    if (novaSenha !== confirmarSenha) {
        showToast("Las nuevas contraseñas no coinciden. Por favor, verifique.", "error");
        return;
    }
    
    try {
        const res = await fetch('/api/admin/credenciais', {
            method: 'POST',
            headers: { ...getSaaSHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({
                senha_atual: senhaAtual,
                novo_login: novoLogin,
                nova_senha: novaSenha
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(data.mensagem || "Credenciales actualizadas correctamente.");
            // Limpar campos
            document.getElementById('seguridad-senha-atual').value = '';
            document.getElementById('seguridad-novo-login').value = '';
            document.getElementById('seguridad-nova-senha').value = '';
            document.getElementById('seguridad-confirmar-senha').value = '';
        } else {
            const error = await res.json();
            showToast(error.detail || "Error al actualizar credenciales", "error");
        }
    } catch (error) {
        console.error('Error:', error);
        showToast("Error de conexión", "error");
    }
}