 let empresaAtualId = null; let rolUsuario = null; let planoAtivo = ''; let productosGlobais = []; let productosCaixa = []; let ncProductosCaixa = []; let remProductosCaixa = []; let autoProductosCaixa = []; let graficoAtual = null; let html5QrCode = null; let campoDestinoScanner = ''; let totalDaVendaAtual = 0; let totalNCTela = 0; let descuentoPorcentaje = 0; let filaContingencia = JSON.parse(localStorage.getItem('nube_fila') || '[]'); let itensEntrada = []; let ultimoCDCGerado = ''; let ultimoQRGerado = ''; let ultimoLinkSifen = '';
    const getSaaSHeaders = (extraHeaders = {}) => { return { 'Content-Type': 'application/json', 'X-Empresa-ID': empresaAtualId ? empresaAtualId.toString() : "1", ...extraHeaders }; };
    
    document.addEventListener("DOMContentLoaded", () => {
        const d = new Date().toISOString().split('T')[0];
        ['filtro-data-inicio-cierre','filtro-data-fim-cierre','entrada-data','filtro-data-fim-var'].forEach(id => {if(document.getElementById(id)) document.getElementById(id).value = d;});
        if(document.getElementById('filtro-data-inicio-var')) { let p = new Date(); p.setDate(1); document.getElementById('filtro-data-inicio-var').value = p.toISOString().split('T')[0]; }
        const toggleStock = document.getElementById('auto-mover-stock');
        if(toggleStock) { toggleStock.addEventListener('change', function() { document.getElementById('auto-stock-status').innerText = this.checked ? "SÍ, añadir al stock" : "NO, es solo un gasto"; document.getElementById('auto-stock-status').className = this.checked ? "text-sm font-bold text-orange-400" : "text-sm font-bold text-gray-500"; }); }
    });

    async function fazerLogin() { 
        const ruc = document.getElementById('login-ruc').value.trim(); const senha = document.getElementById('login-senha').value; 
        const btn = document.getElementById('btn-login'); const erroBox = document.getElementById('erro-login'); 
        if(!ruc || !senha) { erroBox.innerText = "Complete todos los campos."; erroBox.classList.remove('hidden'); return; } 
        btn.innerText = "Verificando..."; btn.disabled = true; 
        try { 
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ruc: ruc, senha: senha}) }); 
            if (res.ok) { 
                const dados = await res.json(); empresaAtualId = dados.empresa_id; rolUsuario = dados.rol; planoAtivo = dados.plano || 'Inicial'; 
                document.getElementById('login-screen').classList.add('hidden'); 
                if (rolUsuario === 'superadmin') { 
                    document.getElementById('app-screen').classList.add('hidden'); document.getElementById('superadmin-screen').classList.remove('hidden'); 
                    carregarEmpresasSaaS(); showToast("¡Bienvenido al Panel Super Admin!"); 
                } else { 
                    document.getElementById('app-screen').classList.remove('hidden'); document.getElementById('app-screen').classList.add('flex'); document.getElementById('mobile-header').classList.remove('hidden'); 
                    document.getElementById('sidebar-rol-loja').innerText = (rolUsuario === 'admin') ? `Dueño | Plan ${planoAtivo.split(' ')[0]}` : `Cajero | Plan ${planoAtivo.split(' ')[0]}`; 
                    
                    const idsTodos = ['nav-group-inventario','nav-btn-dashboard','nav-group-reportes','btn-nav-stocktake','btn-nav-stocktakereport','btn-nav-proveedores','btn-nav-entrada','btn-nav-remision','btn-nav-autofactura','btn-nav-variancia','nav-btn-config','nav-btn-ayuda','btn-cerrar-turno'];
                    idsTodos.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = ''; });
                    if(document.getElementById('box-novo-prov')) document.getElementById('box-novo-prov').style.display = 'block';

                    const isInicial = planoAtivo.includes('Inicial'); const isCrecimiento = planoAtivo.includes('Crecimiento');
                    
                    if (isInicial && rolUsuario === 'admin') {
                        const idsOcultarInicial = ['nav-btn-dashboard', 'btn-nav-stocktake', 'btn-nav-stocktakereport', 'btn-nav-variancia', 'btn-nav-proveedores', 'btn-nav-entrada'];
                        idsOcultarInicial.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; });
                        if(document.getElementById('box-novo-prov')) document.getElementById('box-novo-prov').style.display = 'none';
                    } 
                    if (isCrecimiento && rolUsuario === 'admin') { 
                        const el1 = document.getElementById('btn-nav-stocktakereport'); if(el1) el1.style.display = 'none'; 
                        const el2 = document.getElementById('btn-nav-variancia'); if(el2) el2.style.display = 'none';
                    }
                    if (rolUsuario === 'cajero') { 
                        const idsCajero = ['nav-group-inventario','nav-btn-dashboard','nav-group-reportes','nav-btn-config','btn-cerrar-turno'];
                        idsCajero.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; }); 
                    } 
                    
                    await carregarConfiguracao(); await carregarCategorias(); if(!isInicial) await carregarProveedores(); await carregarEstoque(); checarStatusCaixa(); atualizarStatusConexao(); showToast(`¡Sesión Iniciada!`); 
                } 
            } else { const err = await res.json(); erroBox.innerText = err.detail || err.mensagem || "Credenciales incorrectas."; erroBox.classList.remove('hidden'); } 
        } catch(e) { erroBox.innerText = "Error de red."; erroBox.classList.remove('hidden'); } finally { btn.innerText = "Ingresar al Sistema"; btn.disabled = false; } 
    }

    function prepararTicket(empresaNome, rucEmissor, cdc, cliente, itens, total, qrcode, dataEmissao) {
        let html = `
        <div style="text-align: center; margin-bottom: 10px; font-family: monospace; color: black;">
            <strong style="font-size: 16px;">${empresaNome}</strong><br>
            RUC: ${rucEmissor}<br>
            Factura Electrónica (KuDE)<br>
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
            <img src="${qrcode}" style="width: 150px; height: 150px; margin: 0 auto; display: block;">
            <p style="font-family: monospace; font-size: 10px; margin-top: 5px; color: black;">Consulte mediante el código QR</p>
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
            const texto = encodeURIComponent("¡Hola! Gracias por su compra. Aquí tiene el enlace a su Factura (KuDE): " + ultimoLinkSifen);
            const url = `https://wa.me/${numLimpio}?text=${texto}`;
            
            // Plano B caso o navegador bloqueie a nova aba
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

    function abrirModalEditarEmpresa(id, planoAtual, valorAtual) { document.getElementById('edit-empresa-id').value = id; let p = document.getElementById('edit-plano'); p.value = planoAtual.includes('Inicial') ? 'Inicial' : (planoAtual.includes('Crecimiento') ? 'Crecimiento' : 'VIP'); document.getElementById('edit-valor').value = valorAtual; document.getElementById('modal-editar-empresa').classList.remove('hidden'); document.getElementById('modal-editar-empresa').classList.add('flex'); }
    function fecharModalEditarEmpresa() { document.getElementById('modal-editar-empresa').classList.add('hidden'); document.getElementById('modal-editar-empresa').classList.remove('flex'); }
    async function salvarEdicaoEmpresa() { const id = document.getElementById('edit-empresa-id').value; const plano = document.getElementById('edit-plano').value; const valor = parseFloat(document.getElementById('edit-valor').value) || 0; try { const res = await fetch(`/super-admin/editar-empresa/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({plano: plano, valor_mensalidade: valor}) }); if(res.ok) { showToast("✅ Plan actualizado."); fecharModalEditarEmpresa(); carregarEmpresasSaaS(); } else { showToast("❌ Error.", "error"); } } catch(e) { showToast("❌ Error.", "error"); } }
    async function carregarEmpresasSaaS() { try { const resMet = await fetch('/super-admin/metricas'); if (resMet.ok) { const met = await resMet.json(); document.getElementById('saas-mrr').innerText = met.mrr.toLocaleString('es-PY'); document.getElementById('saas-ativos').innerText = met.clientes_ativos; document.getElementById('saas-vencidos').innerText = met.clientes_vencidos; } const res = await fetch('/super-admin/empresas'); if (res.ok) { const empresas = await res.json(); const tbody = document.getElementById('tabela-saas'); tbody.innerHTML = ''; empresas.forEach(emp => { let corStatus = emp.status === 'Activo' ? 'text-green-400' : 'text-red-400'; tbody.innerHTML += `<tr class="border-b border-slate-700"><td class="p-4 font-bold text-white">${emp.nome}</td><td class="p-4">${emp.ruc}</td><td class="p-4">${emp.plano}</td><td class="p-4 ${corStatus}">${emp.status}</td><td class="p-4"><button onclick="abrirModalEditarEmpresa(${emp.id}, '${emp.plano}', ${emp.valor})" class="text-blue-400">Editar</button></td></tr>`; }); } } catch(e) {} }
    function exportarTabelaParaCSV(idTbody, nomeBase) { const tbody = document.getElementById(idTbody); if(!tbody) return; let csv = []; const linhas = tbody.closest('table').querySelectorAll('tr'); for(let i=0;i<linhas.length;i++){ let l=[]; const cols = linhas[i].querySelectorAll('td, th'); for(let j=0;j<cols.length;j++) l.push('"'+cols[j].innerText.replace(/"/g,'""')+'"'); csv.push(l.join(',')); } const blob = new Blob(["\uFEFF"+csv.join('\n')], {type:'text/csv;charset=utf-8;'}); const link=document.createElement("a"); link.href=URL.createObjectURL(blob); link.download=`${nomeBase}.csv`; link.click(); }
    function abrirModalLegal() { document.getElementById('modal-legal').classList.remove('hidden'); document.getElementById('modal-legal').classList.add('flex'); } function fecharModalLegal() { document.getElementById('modal-legal').classList.add('hidden'); document.getElementById('modal-legal').classList.remove('flex'); }
    function fecharModalAudit() { document.getElementById('modal-audit-details').classList.add('hidden'); document.getElementById('modal-audit-details').classList.remove('flex'); }
    function atualizarStatusConexao() { const badge = document.getElementById('badge-conexao'); if (navigator.onLine) { badge.className = "bg-green-900/30 text-green-400 px-3 py-1 rounded-full text-xs font-bold"; badge.innerHTML = `Online`; if (filaContingencia.length > 0) sincronizarFila(); } else { badge.classList.remove('hidden'); badge.className = "bg-red-900/30 text-red-400 px-3 py-1 rounded-full text-xs font-bold animate-pulse"; badge.innerHTML = `Offline (${filaContingencia.length})`; } } window.addEventListener('online', atualizarStatusConexao); window.addEventListener('offline', atualizarStatusConexao);
    function showToast(message, type = 'success') { const container = document.getElementById('toast-container'); const toast = document.createElement('div'); toast.className = `text-white p-4 rounded-lg shadow-lg min-w-[300px] toast-enter relative overflow-hidden ${type==='success'?'bg-brand-accent':(type==='error'?'bg-red-600':'bg-yellow-500')}`; toast.innerHTML = `<p class="font-bold text-sm">${message}</p>`; container.appendChild(toast); requestAnimationFrame(() => { toast.classList.remove('toast-enter'); toast.classList.add('toast-enter-active'); }); setTimeout(() => { toast.classList.remove('toast-enter-active'); toast.classList.add('toast-exit-active'); setTimeout(() => container.removeChild(toast), 300); }, 3000); }
    function toggleSidebar() { document.getElementById('sidebar').classList.toggle('-translate-x-full'); document.getElementById('overlay').classList.toggle('hidden'); } function toggleAcordeao(menuId, setaId) { const menu = document.getElementById(menuId); const seta = document.getElementById(setaId); if(menu.classList.contains('hidden')) { menu.classList.remove('hidden'); menu.classList.add('flex'); seta.innerText = '▲'; } else { menu.classList.add('hidden'); menu.classList.remove('flex'); seta.innerText = '▼'; } } 
    
    function mudarTela(telaId, elementoBotao) { 
        document.querySelectorAll('.section-tela').forEach(t => t.classList.add('hidden')); 
        const telaAlvo = document.getElementById('tela-' + telaId);
        if(telaAlvo) telaAlvo.classList.remove('hidden'); 
        
        if(elementoBotao !== null) { document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('menu-ativo')); elementoBotao.classList.add('menu-ativo'); } 
        if(window.innerWidth < 768) { document.getElementById('sidebar').classList.add('-translate-x-full'); document.getElementById('overlay').classList.add('hidden'); } 
        
        if(['inventario','pos','entrada','operaciones','remision','autofactura'].includes(telaId)) carregarEstoque();
        if(telaId === 'proveedores') carregarProveedores(); if(telaId === 'stocktake') carregarStockTake(); if(telaId === 'variancia') carregarRelatorioVariancia();
        if(telaId === 'operaciones') { document.getElementById('nc-cdc').value=''; document.getElementById('nc-cliente').value=''; ncProductosCaixa=[]; atualizarInterfaceNC(); document.getElementById('merma-cod').value=''; carregarMermas(); }
        if(telaId === 'remision') { carregarRemisiones(); remProductosCaixa=[]; atualizarInterfaceRemision(); }
        if(telaId === 'autofactura') { carregarAutofacturas(); autoProductosCaixa=[]; atualizarInterfaceAuto(); }
        if(telaId === 'reportes') carregarHistorico(); if(telaId === 'cierre') carregarCierreCaja(); if(telaId === 'config') carregarConfiguracao(); if(telaId === 'categorias') carregarCategorias(); if(telaId === 'dashboard') carregarDashboard(); 
        if(telaId === 'pos') checarStatusCaixa(); 
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
        // Esconde a caixa de troco para Cartão, Transferência e PIX
        boxVuelto.classList.add('hidden'); 
    } 
}
    
    async function confirmarVenta() { 
        const metodoPago = document.getElementById('checkout-metodo').value; 
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
            fecharCheckout(); 
            document.getElementById('resultado').classList.remove('hidden'); 
            document.getElementById('btn-pdf').href = dados.link_pdf; 
            
            ultimoCDCGerado = dados.cdc;
            ultimoLinkSifen = window.location.origin + dados.link_pdf; 
            ultimoQRGerado = `https://quickchart.io/qr?text=${encodeURIComponent(dados.link_qrcode)}&size=150`;
            
            document.getElementById('qrcode-img').src = ultimoQRGerado; 
            
            document.getElementById('btn-emitir').classList.add('hidden'); 
            atualizarInterfaceCaixa(); 
        } catch(e) { showToast("❌ Error.", "error"); } finally { btn.disabled = false; } 
    }
    
    function novaVenda() { document.getElementById('resultado').classList.add('hidden'); document.getElementById('btn-emitir').classList.remove('hidden'); document.getElementById('cliente').value = ''; descuentoPorcentaje = 0; productosCaixa = []; atualizarInterfaceCaixa(); }
    async function sincronizarFila() { if (filaContingencia.length === 0 || !navigator.onLine) return; let pendentes = [...filaContingencia]; filaContingencia = []; let sucesso = 0; for (let n of pendentes) { try { const res = await fetch('/emitir-nota', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(n) }); if (res.ok) sucesso++; else filaContingencia.push(n); } catch(e) { filaContingencia.push(n); } } localStorage.setItem('nube_fila', JSON.stringify(filaContingencia)); atualizarStatusConexao(); if(sucesso>0) showToast(`✅ ${sucesso} sincronizadas.`); }
    
    function abrirCamera(idCampo) { campoDestinoScanner = idCampo; document.getElementById('camera-modal').classList.remove('hidden'); document.getElementById('camera-modal').classList.add('flex'); if (!html5QrCode) html5QrCode = new Html5Qrcode("reader"); html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 250, height: 150 } }, onScanSucesso, ()=>{}); } 
    function onScanSucesso(codigo) { fecharCamera(); document.getElementById(campoDestinoScanner).value = codigo; if (campoDestinoScanner === 'scanner-barras') verificarScanner({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'entrada-scanner') buscarProdutoEntrada({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'nc-scanner') verificarScannerNC({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'merma-cod') buscarParaMerma({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'rem-scanner') verificarScannerRemision({key:'Enter',preventDefault:()=>{}}); else if (campoDestinoScanner === 'auto-scanner') verificarScannerAuto({key:'Enter',preventDefault:()=>{}}); } 
    function fecharCamera() { document.getElementById('camera-modal').classList.add('hidden'); if(html5QrCode) html5QrCode.stop().then(()=>html5QrCode.clear()); }
    
    let isScanning = false; function filtrarPOS() { const input = document.getElementById('scanner-barras').value.toLowerCase(); const dropdown = document.getElementById('pos-dropdown'); dropdown.innerHTML = ''; if (input.length < 2) { dropdown.classList.add('hidden'); return; } const resultados = productosGlobais.filter(p => p.descricao.toLowerCase().includes(input) || p.codigo_barras.toLowerCase().includes(input)).slice(0, 10); if (resultados.length > 0) { dropdown.classList.remove('hidden'); resultados.forEach(p => { const div = document.createElement('div'); div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white'; div.innerHTML = `<span>${p.descricao}</span><span class="text-brand-accent">Gs. ${p.preco_venda.toLocaleString('es-PY')}</span>`; div.onclick = () => seleccionarProductoPOS(p); dropdown.appendChild(div); }); } else { dropdown.classList.add('hidden'); } }
    function seleccionarProductoPOS(prod) { document.getElementById('pos-dropdown').classList.add('hidden'); document.getElementById('scanner-barras').value = ''; const idx = productosCaixa.findIndex(p => p.codigo_barras === prod.codigo_barras); if (idx !== -1) productosCaixa[idx].quantidade += 1; else productosCaixa.push({ codigo_barras: prod.codigo_barras, descricao: prod.descricao, quantidade: 1, preco_unitario: parseFloat(prod.preco_venda) }); atualizarInterfaceCaixa(); }
    async function verificarScanner(e) { if(e && e.key === 'Enter') { if(e.preventDefault) e.preventDefault(); if(isScanning) return; isScanning = true; const codigo = document.getElementById('scanner-barras').value.trim(); document.getElementById('scanner-barras').value = ''; document.getElementById('pos-dropdown').classList.add('hidden'); try { const idx = productosCaixa.findIndex(p => p.codigo_barras === codigo); if (idx !== -1) { productosCaixa[idx].quantidade += 1; atualizarInterfaceCaixa(); } else { const pGlobal = productosGlobais.find(p=>p.codigo_barras === codigo); if(pGlobal) seleccionarProductoPOS(pGlobal); else { const res = await fetch('/buscar-produto/'+codigo, {headers:getSaaSHeaders()}); if(res.ok) { const p = await res.json(); productosCaixa.push({codigo_barras:codigo, descricao:p.descricao, quantidade:1, preco_unitario:parseFloat(p.preco)}); atualizarInterfaceCaixa(); } } } } catch(err){} finally{ setTimeout(()=>isScanning=false, 300); } } }
    function pedirDescuento() { const desc = prompt("Descuento (%):"); if(desc) { descuentoPorcentaje = parseFloat(desc) || 0; atualizarInterfaceCaixa(); } } function alterarQuantidade(idx, delta) { productosCaixa[idx].quantidade += delta; if(productosCaixa[idx].quantidade <= 0) productosCaixa.splice(idx,1); atualizarInterfaceCaixa(); }
    function atualizarInterfaceCaixa() { const tbody = document.getElementById('lista-produtos'); tbody.innerHTML = ''; let sub = 0; productosCaixa.forEach((p, i) => { const st = p.quantidade * p.preco_unitario; sub += st; tbody.innerHTML += `<div class="bg-slate-700/50 p-3 rounded-lg flex justify-between items-center mb-2"><div><span class="text-white block">${p.descricao}</span></div><div class="flex items-center gap-2"><button onclick="alterarQuantidade(${i},-1)" class="text-brand-accent px-2 font-bold">-</button><span class="text-white">${p.quantidade}</span><button onclick="alterarQuantidade(${i},1)" class="text-brand-accent px-2 font-bold">+</button><span class="text-brand-accent w-24 text-right">Gs. ${st.toLocaleString('es-PY')}</span></div></div>`; }); const descV = sub*(descuentoPorcentaje/100); totalDaVendaAtual = sub - descV; document.getElementById('subtotal-tela').innerText = sub.toLocaleString('es-PY'); document.getElementById('descuento-tela').innerText = descV.toLocaleString('es-PY'); document.getElementById('valor-total-tela').innerText = totalDaVendaAtual.toLocaleString('es-PY'); }
    
    function toggleFormProducto() { document.getElementById('form-novo-produto').classList.toggle('hidden'); } function filtrarEstoque() { const termo=document.getElementById('busca-inventario').value.toLowerCase(); const cat=document.getElementById('filtro-cat-inventario').value; const res=productosGlobais.filter(p=>(p.descricao.toLowerCase().includes(termo)||p.codigo_barras.toLowerCase().includes(termo))&&(cat===""||p.categoria===cat)); const tbody=document.getElementById('tabela-estoque'); tbody.innerHTML=''; res.forEach(p=>{ tbody.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 font-bold text-white">${p.descricao}<br><span class="text-xs text-gray-400 font-mono">${p.codigo_barras}</span></td><td class="p-4">${p.categoria}</td><td class="p-4">${p.codigo_proveedor||'-'}</td><td class="p-4 text-right text-white">Gs. ${p.preco_venda.toLocaleString('es-PY')}</td><td class="p-4 text-center font-bold text-brand-accent">${p.quantidade}</td><td class="p-4"><button onclick="deletarProduto('${p.codigo_barras}')" class="text-red-400">🗑️</button></td></tr>`; }); }
    async function carregarEstoque() { try { const res = await fetch('/listar-produtos', {headers:getSaaSHeaders()}); productosGlobais = await res.json(); filtrarEstoque(); if(document.getElementById('tela-stocktake') && !document.getElementById('tela-stocktake').classList.contains('hidden')) renderTabelaStockTake(productosGlobais); } catch(e){} }
    function calcularLucro() { const c = parseFloat(document.getElementById('novo-custo').value)||0; const v = parseFloat(document.getElementById('novo-preco').value)||0; if(v>0 && c>=0) { document.getElementById('info-lucro').innerText = `GP: ${((v-c)/v*100).toFixed(1)}%`; document.getElementById('info-lucro').className="text-green-400 text-xs"; } }
    async function cadastrarProduto() { const d = { codigo_barras: document.getElementById('novo-cod').value, descricao: document.getElementById('novo-desc').value, categoria: document.getElementById('novo-cat').value, subcategoria: "-", preco_custo: parseFloat(document.getElementById('novo-custo').value)||0, preco_venda: parseFloat(document.getElementById('novo-preco').value)||0, quantidade: parseInt(document.getElementById('novo-qtd').value)||0, codigo_proveedor: document.getElementById('novo-prov')?.value||"" }; try { await fetch('/cadastrar-produto', {method:'POST',headers:getSaaSHeaders(),body:JSON.stringify(d)}); carregarEstoque(); toggleFormProducto(); } catch(e){} }
    async function deletarProduto(cod) { if(confirm("Eliminar?")) { await fetch(`/deletar-produto/${cod}`, {method:'DELETE',headers:getSaaSHeaders()}); carregarEstoque(); } }
    async function carregarCierreCaja() { const i=document.getElementById('filtro-data-inicio-cierre').value; const f=document.getElementById('filtro-data-fim-cierre').value; try { const res = await fetch(`/cierre-caja?inicio=${i}&fim=${f}`, {headers:getSaaSHeaders()}); const d = await res.json(); document.getElementById('cierre-vendas').innerText = d.vendas_hoje.toLocaleString('es-PY'); document.getElementById('cierre-gp').innerText = d.lucro_bruto.toLocaleString('es-PY'); document.getElementById('cierre-sangrias').innerText = d.total_sangrias.toLocaleString('es-PY'); document.getElementById('cierre-notas').innerText = d.notas_emitidas; const tb=document.getElementById('tabela-cierre-itens'); tb.innerHTML=''; d.detalhes_itens.forEach(it=>{ tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-3 text-white">${it.descricao}</td><td class="p-3 text-center">${it.vendidos}</td><td class="p-3 text-right">Gs. ${it.preco_venda.toLocaleString('es-PY')}</td><td class="p-3 text-right">Gs. ${it.receita_total.toLocaleString('es-PY')}</td><td class="p-3 text-right text-green-400">Gs. ${it.lucro_total.toLocaleString('es-PY')}</td><td class="p-3 text-center">${it.margem}%</td></tr>`; }); } catch(e){} }
    
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
    
    async function carregarDashboard() { try { const res=await fetch('/dados-dashboard', {headers:getSaaSHeaders()}); const d=await res.json(); document.getElementById('dash-vendas').innerText=d.total_vendas.toLocaleString('es-PY'); document.getElementById('dash-notas').innerText=d.total_notas; const ctx=document.getElementById('grafico-produtos').getContext('2d'); if(graficoAtual) graficoAtual.destroy(); graficoAtual=new Chart(ctx,{type:'bar',data:{labels:d.top_produtos.map(p=>p.nome),datasets:[{label:'Unidades',data:d.top_produtos.map(p=>p.quantidade),backgroundColor:'#0d9488'}]},options:{responsive:true,maintainAspectRatio:false}}); } catch(e){} }
    async function carregarCategorias() { try { const res=await fetch('/listar-categorias', {headers:getSaaSHeaders()}); const d=await res.json(); const sf=document.getElementById('novo-cat'); const sfi=document.getElementById('filtro-cat-inventario'); const tb=document.getElementById('tabela-categorias'); if(sf) sf.innerHTML=''; if(sfi) sfi.innerHTML='<option value="">Todas</option>'; if(tb) tb.innerHTML=''; d.forEach(c=>{ if(sf) sf.innerHTML+=`<option value="${c.nome}">${c.nome}</option>`; if(sfi) sfi.innerHTML+=`<option value="${c.nome}">${c.nome}</option>`; if(tb) tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${c.nome}</td><td class="p-4 text-center"><button onclick="deletarCategoria(${c.id})" class="text-red-400">🗑️</button></td></tr>`; }); } catch(e){} }
    async function adicionarCategoria() { const n=document.getElementById('nova-cat-nome').value; if(n){ await fetch('/cadastrar-categoria',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({nome:n})}); carregarCategorias(); document.getElementById('nova-cat-nome').value=''; } } async function deletarCategoria(id) { if(confirm("Del?")) { await fetch(`/deletar-categoria/${id}`,{method:'DELETE',headers:getSaaSHeaders()}); carregarCategorias(); } }
  async function carregarConfiguracao() { 
    try { 
        const res = await fetch('/obter-configuracao', {headers: getSaaSHeaders()}); 
        const d = await res.json(); 
        
        if(d){ 
            if(document.getElementById('conf-nome')) document.getElementById('conf-nome').value=d.nome_empresa || ''; 
            if(document.getElementById('conf-ruc')) document.getElementById('conf-ruc').value=d.ruc || ''; 
            if(document.getElementById('conf-endereco')) document.getElementById('conf-endereco').value=d.endereco || ''; 
            if(document.getElementById('conf-senha-cert')) document.getElementById('conf-senha-cert').value=d.senha_certificado || ''; 
            if(document.getElementById('conf-csc')) document.getElementById('conf-csc').value=d.csc || ''; 
            
            // ESTA É A LINHA QUE COLOCA O TOKEN DE VOLTA NA CAIXINHA
            if(document.getElementById('conf-mp-token')) document.getElementById('conf-mp-token').value=d.mercado_pago_token || ''; 
            
            if(document.getElementById('ruc')) document.getElementById('ruc').value=d.ruc || ''; 
            if(document.getElementById('conf-ambiente')) document.getElementById('conf-ambiente').value=d.ambiente_sifen || 'testes'; 
            if(document.getElementById('sidebar-nome-loja')) document.getElementById('sidebar-nome-loja').innerText=d.nome_empresa || 'Empresa'; 
        } 
    } catch(e){} 
}
    async function alterarAmbienteSifen() { await fetch('/alternar-ambiente',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({ambiente:document.getElementById('conf-ambiente').value})}); }
    async function salvarConfiguracao() { 
    const f=new FormData(); 
    f.append('nome_empresa',document.getElementById('conf-nome').value); 
    f.append('ruc',document.getElementById('conf-ruc').value); 
    f.append('endereco',document.getElementById('conf-endereco').value); 
    f.append('senha_certificado',document.getElementById('conf-senha-cert').value); 
    if(document.getElementById('conf-csc')) f.append('csc',document.getElementById('conf-csc').value); 
    
    // NOVO: Envia o token para o Python
    if(document.getElementById('conf-mp-token')) f.append('mercado_pago_token',document.getElementById('conf-mp-token').value); 

    await fetch('/salvar-configuracao',{method:'POST',headers:{'X-Empresa-ID':empresaAtualId.toString()},body:f}); 
    showToast("✅ Configuración General Guardada"); 
}
    async function fazerUploadCertificado() { const file=document.getElementById('arquivo-cert').files[0]; if(file){ const f=new FormData(); f.append('arquivo',file); await fetch('/upload-certificado',{method:'POST',headers:{'X-Empresa-ID':empresaAtualId.toString()},body:f}); showToast("✅ Subido"); } }
    async function carregarStockTake() { await carregarEstoque(); renderTabelaStockTake(productosGlobais); } function filtrarListaStockTake() { const t=document.getElementById('busca-st').value.toLowerCase(); renderTabelaStockTake(productosGlobais.filter(p=>p.descricao.toLowerCase().includes(t)||p.codigo_barras.toLowerCase().includes(t))); } function renderTabelaStockTake(l) { const tb=document.getElementById('tabela-stocktake'); tb.innerHTML=''; l.forEach(p=>{ let val=document.getElementById(`st-input-${p.codigo_barras}`)?.value||''; tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${p.descricao}</td><td class="p-4 text-center font-bold text-brand-accent">${p.quantidade}</td><td class="p-4 text-center"><input type="number" id="st-input-${p.codigo_barras}" value="${val}" class="w-24 p-2 bg-slate-800 text-center text-white border border-slate-600 rounded" oninput="atualizarDiffST('${p.codigo_barras}',${p.quantidade})"></td><td class="p-4 text-center"><span id="st-diff-${p.codigo_barras}">-</span></td></tr>`; if(val!=='') atualizarDiffST(p.codigo_barras,p.quantidade); }); } function atualizarDiffST(c,q) { let val=document.getElementById(`st-input-${c}`).value; let sp=document.getElementById(`st-diff-${c}`); if(val==='') sp.innerText='-'; else { let d=parseInt(val)-q; sp.innerText=d>0?`+${d}`:d; sp.className=d>0?'text-green-400 font-bold':(d<0?'text-red-400 font-bold':'text-gray-400 font-bold'); } } async function salvarStockTake() { let pay=[]; productosGlobais.forEach(p=>{ let v=document.getElementById(`st-input-${p.codigo_barras}`); if(v&&v.value!=='') if(parseInt(v.value)!==p.quantidade) pay.push({codigo_barras:p.codigo_barras,qtd_fisica:parseInt(v.value)}); }); if(pay.length>0) { await fetch('/salvar-auditoria',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({itens:pay})}); showToast("✅ Audit OK"); carregarStockTake(); } }
    
    async function carregarRelatorioVariancia() { const i=document.getElementById('filtro-data-inicio-var').value; const f=document.getElementById('filtro-data-fim-var').value; try { const res=await fetch(`/relatorio-variancia?inicio=${i}&fim=${f}`, {headers:getSaaSHeaders()}); const d=await res.json(); const tb=document.getElementById('tabela-variancia'); tb.innerHTML=''; let imp=0; let un=0; if(d.length===0){ tb.innerHTML='<tr><td colspan="3" class="text-center p-6 text-gray-500">Nada</td></tr>'; document.getElementById('var-impacto-total').innerText=0; document.getElementById('var-unidades-total').innerText=0; return; } d.forEach(x=>{ imp+=x.impacto_total; un+=Math.abs(x.total_diferenca); let c = x.total_diferenca>0?'text-green-400':'text-red-400'; tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${x.descricao}</td><td class="p-4 text-center font-bold ${c}">${x.total_diferenca}</td><td class="p-4 text-right font-bold ${c}">${x.impacto_total.toLocaleString('es-PY')}</td></tr>`; }); document.getElementById('var-unidades-total').innerText=un; document.getElementById('var-impacto-total').innerText=`Gs. ${imp.toLocaleString('es-PY')}`; document.getElementById('var-impacto-total').className=`text-3xl font-bold ${imp>0?'text-green-400':'text-red-400'}`; } catch(e){} }
    
    async function carregarProveedores() { try { const res=await fetch('/listar-proveedores', {headers:getSaaSHeaders()}); const d=await res.json(); const tb=document.getElementById('tabela-proveedores'); if(tb) { tb.innerHTML=''; d.forEach(p=>{ tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-4 text-white">${p.nome}</td><td class="p-4 text-gray-400">${p.telefone||''}</td><td class="p-4">${p.endereco||''}</td><td class="p-4"><button onclick="abrirModalEditarProveedor(${p.id},'${p.nome}','${p.ruc}','${p.telefone}','${p.email}','${p.endereco}')" class="text-blue-400 mr-2">✏️</button><button onclick="deletarProveedor(${p.id})" class="text-red-400">🗑️</button></td></tr>`; }); } const sp=document.getElementById('novo-prov'); if(sp) { sp.innerHTML='<option value="">Ninguno</option>'; d.forEach(p=>{ sp.innerHTML+=`<option value="${p.nome}">${p.nome}</option>`; }); } const sep=document.getElementById('entrada-prov'); if(sep) { sep.innerHTML='<option value="">Seleccione</option>'; d.forEach(p=>{ sep.innerHTML+=`<option value="${p.id}">${p.nome}</option>`; }); } } catch(e){} }
    function abrirModalEditarProveedor(id, n, r, t, e, end) { document.getElementById('prov-id').value=id; document.getElementById('prov-nome').value=n; document.getElementById('prov-ruc').value=r!=='null'?r:''; document.getElementById('prov-tel').value=t!=='null'?t:''; document.getElementById('prov-email').value=e!=='null'?e:''; document.getElementById('prov-endereco').value=end!=='null'?end:''; document.getElementById('form-novo-proveedor').classList.remove('hidden'); }
    async function salvarProveedor() { const id=document.getElementById('prov-id').value; const pay={nome:document.getElementById('prov-nome').value, ruc:document.getElementById('prov-ruc').value, telefone:document.getElementById('prov-tel').value, email:document.getElementById('prov-email').value, endereco:document.getElementById('prov-endereco').value}; const url=id?`/editar-proveedor/${id}`:'/cadastrar-proveedor'; const m=id?'PUT':'POST'; try { await fetch(url,{method:m,headers:getSaaSHeaders(),body:JSON.stringify(pay)}); document.getElementById('form-novo-proveedor').classList.add('hidden'); carregarProveedores(); } catch(e){} } async function deletarProveedor(id) { if(confirm("Del?")) { await fetch(`/deletar-proveedor/${id}`,{method:'DELETE',headers:getSaaSHeaders()}); carregarProveedores(); } }
    
    function buscarProdutoEntrada(e) { if(e.key==='Enter') { e.preventDefault(); const c=document.getElementById('entrada-scanner').value; const p=productosGlobais.find(x=>x.codigo_barras===c); if(p){ const q=prompt(`Cant de ${p.descricao}:`); if(!q) return; const cost=prompt(`Costo:`, p.preco_custo); if(!cost) return; itensEntrada.push({codigo_barras:c, descricao:p.descricao, quantidade:parseInt(q), custo_unitario:parseFloat(cost)}); atualizarInterfaceEntrada(); document.getElementById('entrada-scanner').value=''; } } }
    function atualizarInterfaceEntrada() { const tb=document.getElementById('tabela-entrada-itens'); tb.innerHTML=''; let t=0; itensEntrada.forEach((i,idx)=>{ const st=i.quantidade*i.custo_unitario; t+=st; tb.innerHTML+=`<tr class="border-b border-slate-700"><td class="p-3 text-white">${i.descricao}</td><td class="p-3 text-center text-white">${i.quantidade}</td><td class="p-3 text-right">Gs. ${i.custo_unitario.toLocaleString('es-PY')}</td><td class="p-3 text-right font-bold text-blue-400">Gs. ${st.toLocaleString('es-PY')}</td><td class="p-3 text-center"><button onclick="itensEntrada.splice(${idx},1);atualizarInterfaceEntrada();" class="text-red-400">✕</button></td></tr>`; }); document.getElementById('entrada-total-tela').innerText=t.toLocaleString('es-PY'); }
    async function salvarEntradaFactura() { if(itensEntrada.length===0) return; const p=document.getElementById('entrada-prov').value; const n=document.getElementById('entrada-nro').value; const d=document.getElementById('entrada-data').value; if(!p||!n) return showToast("Falta info", "error"); try { await fetch('/salvar-entrada',{method:'POST',headers:getSaaSHeaders(),body:JSON.stringify({proveedor_id:parseInt(p), numero_factura:n, data_emissao:d, itens:itensEntrada})}); showToast("✅ Factura Guardada"); itensEntrada=[]; atualizarInterfaceEntrada(); document.getElementById('entrada-nro').value=''; carregarEstoque(); } catch(e){} }
    
    function filtrarMerma() { const inp = document.getElementById('merma-cod').value.toLowerCase(); const drop = document.getElementById('merma-dropdown'); drop.innerHTML = ''; if (inp.length < 2) { drop.classList.add('hidden'); return; } const res = productosGlobais.filter(p => p.descricao.toLowerCase().includes(inp) || p.codigo_barras.toLowerCase().includes(inp)).slice(0, 10); if (res.length > 0) { drop.classList.remove('hidden'); res.forEach(p => { const div = document.createElement('div'); div.className = 'p-3 border-b border-slate-600 hover:bg-slate-600 cursor-pointer text-white'; div.innerHTML = p.descricao; div.onclick = () => { drop.classList.add('hidden'); document.getElementById('merma-cod').value = p.codigo_barras; document.getElementById('merma-atual').value = p.quantidade; document.getElementById('merma-add').focus(); }; drop.appendChild(div); }); } else { drop.classList.add('hidden'); } }
    function buscarParaMerma(e) { if(e.key === 'Enter') { e.preventDefault(); const c = document.getElementById('merma-cod').value.trim(); const p = productosGlobais.find(x => x.codigo_barras === c); if(p) { document.getElementById('merma-dropdown').classList.add('hidden'); document.getElementById('merma-cod').value = p.codigo_barras; document.getElementById('merma-atual').value = p.quantidade; document.getElementById('merma-add').focus(); } } }
    async function salvarMerma() { const c = document.getElementById('merma-cod').value; const q = parseInt(document.getElementById('merma-add').value); const m = document.getElementById('merma-motivo').value; if(!c || !q || q<=0) return; try { const res = await fetch('/registrar-merma', { method:'POST', headers:getSaaSHeaders(), body:JSON.stringify({codigo_barras:c, quantidade:q, motivo:m}) }); if(res.ok) { showToast("✅ Baja registrada."); document.getElementById('merma-cod').value=''; document.getElementById('merma-atual').value=''; document.getElementById('merma-add').value=''; carregarMermas(); carregarEstoque(); } else { const err = await res.json(); showToast("❌ " + err.detail, "error"); } } catch(e){} }
    async function carregarMermas() { try { const res = await fetch('/listar-mermas', {headers:getSaaSHeaders()}); const d = await res.json(); const tb = document.getElementById('tabela-mermas'); tb.innerHTML = ''; d.forEach(m => { const loss = m.quantidade * m.custo; tb.innerHTML += `<tr class="border-b border-slate-700 hover:bg-slate-700/30"><td class="p-3 text-gray-400 text-xs">${m.data}</td><td class="p-3 text-white font-bold">${m.descricao}</td><td class="p-3 text-center text-red-400 font-bold">${m.quantidade}</td><td class="p-3 text-gray-400">${m.motivo}</td><td class="p-3 text-right text-red-400 font-bold">Gs. ${loss.toLocaleString('es-PY')}</td></tr>`; }); } catch(e){} }

    function filtrarNC() { const input = document.getElementById('nc-scanner').value.toLowerCase(); const dropdown = document.getElementById('nc-dropdown'); dropdown.innerHTML = ''; if (input.length < 2) { dropdown.classList.add('hidden'); return; } const resultados = productosGlobais.filter(p => p.descricao.toLowerCase().includes(input) || p.codigo_barras.toLowerCase().includes(input)).slice(0, 10); if (resultados.length > 0) { dropdown.classList.remove('hidden'); resultados.forEach(p => { const div = document.createElement('div'); div.className = 'p-4 hover:bg-slate-700/50 cursor-pointer border-b border-slate-700 flex justify-between text-white'; div.innerHTML = `<span>${p.descricao}</span><span class="text-purple-400 font-bold">Gs. ${p.preco_venda.toLocaleString('es-PY')}</span>`; div.onclick = () => seleccionarProdutoNC(p); dropdown.appendChild(div); }); } else { dropdown.classList.add('hidden'); } }
    function seleccionarProdutoNC(prod) { document.getElementById('nc-dropdown').classList.add('hidden'); document.getElementById('nc-scanner').value = ''; const idx = ncProductosCaixa.findIndex(p => p.codigo_barras === prod.codigo_barras); if (idx !== -1) ncProductosCaixa[idx].quantidade += 1; else ncProductosCaixa.push({ codigo_barras: prod.codigo_barras, descricao: prod.descricao, quantidade: 1, preco_unitario: Number(prod.preco_venda) }); atualizarInterfaceNC(); }
    function verificarScannerNC(e) { if(e && e.key === 'Enter') { e.preventDefault(); const codigo = document.getElementById('nc-scanner').value.trim(); document.getElementById('nc-scanner').value = ''; document.getElementById('nc-dropdown').classList.add('hidden'); const pGlobal = productosGlobais.find(p=>p.codigo_barras === codigo); if(pGlobal) seleccionarProdutoNC(pGlobal); } }
    function atualizarInterfaceNC() { const tbody = document.getElementById('nc-lista-produtos'); tbody.innerHTML = ''; let sub = 0; ncProductosCaixa.forEach((p, i) => { const st = p.quantidade * p.preco_unitario; sub += st; tbody.innerHTML += `<div class="bg-slate-700/50 p-3 rounded-lg flex justify-between items-center mb-2"><div><span class="text-white block">${p.descricao}</span></div><div class="flex items-center gap-3"><span class="text-white font-bold">${p.quantidade} unid.</span><span class="font-bold text-purple-400 w-24 text-right">Gs. ${st.toLocaleString('es-PY')}</span><button onclick="ncProductosCaixa.splice(${i}, 1); atualizarInterfaceNC();" class="text-red-400 font-bold bg-red-900/20 px-2 rounded">✕</button></div></div>`; }); totalNCTela = sub; document.getElementById('nc-valor-total-tela').innerText = sub.toLocaleString('es-PY'); }
    async function emitirNotaCredito() { const cdcRef = document.getElementById('nc-cdc').value.trim(); const cl = document.getElementById('nc-cliente').value.trim(); if(ncProductosCaixa.length === 0 || !cdcRef || !cl) return showToast("Complete todo.", "warning"); const btn = document.getElementById('btn-emitir-nc'); btn.disabled = true; const payload = { ruc_emissor: document.getElementById('ruc').value, nome_cliente: cl, valor_total: totalNCTela, itens: ncProductosCaixa, cdc_referencia: cdcRef, metodo_pago: "Devolucion" }; try { const res = await fetch('/emitir-nota', { method: 'POST', headers: getSaaSHeaders(), body: JSON.stringify(payload) }); const dados = await res.json(); document.getElementById('nc-resultado').classList.remove('hidden'); document.getElementById('btn-nc-pdf').href = dados.link_pdf; btn.classList.add('hidden'); ncProductosCaixa = []; atualizarInterfaceNC(); carregarEstoque(); } catch(e) {} finally { btn.disabled = false; } }
    function novaNC() { document.getElementById('nc-resultado').classList.add('hidden'); document.getElementById('btn-emitir-nc').classList.remove('hidden'); document.getElementById('nc-cdc').value = ''; document.getElementById('nc-cliente').value = ''; document.getElementById('nc-scanner').focus(); }
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