"""Regresiones de la revisión del PR #12."""
import random
import json
from test_iteracion5_recomendacion import proceso, recibir, hecho_cancelacion
from simuladores.datos_sinteticos import vuelo_cancelado
from simuladores.proveedores import ErrorTemporal
from recomendacion.modelo.caracteristicas import cumple_limites, PESOS_INICIALES


def test_presupuesto_no_omite_moneda_distinta():
    oferta = {'price': {'amount': 10000, 'currency': 'EUR'}, 'provider': 'p'}
    assert not cumple_limites(oferta, {'maxPrice': {'amount': 100, 'currency': 'USD'}})
    assert not cumple_limites(oferta, {'maxPrice': {'amount': 100, 'currency': 'EUR'}})
    assert cumple_limites(oferta, {'maxPrice': {'amount': 10000, 'currency': 'EUR'}})


def test_parcial_se_completa_sin_duplicar_y_conserva_rechazo(proceso):
    proceso.apis['aerolinea-norte'].fallar_proxima(ErrorTemporal('caido'))
    recibir(proceso, hecho_cancelacion('u', vuelo_cancelado(random.Random(2))))
    proceso.ciclo()
    trip = 'sa-east:viaje-u'
    primera = proceso.sugerencias.listar('u', trip)
    assert primera['searchStatus'] == 'partial'
    rechazada = primera['suggestions'][0]['id']
    proceso.sugerencias.feedback('u', rechazada, 'reject')
    proceso.reloj.adelantar(minutes=2)
    proceso.ciclo()
    assert proceso.sugerencias.listar('u', trip)['searchStatus'] == 'ready'
    assert proceso.buscador.consultas['aerolinea-norte'] == 2
    with proceso.base.transaccion() as tx:
        filas = tx.todos('SELECT suggestion_id, oferta, estado FROM sugerencias')
        assert tx.uno('SELECT estado FROM sugerencias WHERE suggestion_id = ?', (rechazada,))['estado'] == 'rejected'
    claves = [(json.loads(f['oferta'])['provider'], json.loads(f['oferta'])['offerId']) for f in filas]
    assert len(claves) == len(set(claves))
    antes = dict(proceso.buscador.consultas)
    proceso.reloj.adelantar(minutes=3)
    proceso.ciclo()
    assert proceso.buscador.consultas == antes


def test_aceptar_parcial_detiene_busqueda(proceso):
    proceso.apis['aerolinea-norte'].fallar_proxima(ErrorTemporal('caido'))
    recibir(proceso, hecho_cancelacion('u', vuelo_cancelado(random.Random(2))))
    proceso.ciclo()
    sugerencia = proceso.sugerencias.listar('u', 'sa-east:viaje-u')['suggestions'][0]
    proceso.sugerencias.feedback('u', sugerencia['id'], 'accept')
    antes = dict(proceso.buscador.consultas)
    proceso.reloj.adelantar(minutes=3)
    proceso.ciclo()
    assert proceso.buscador.consultas == antes


def test_rollback_salta_canario_descartado(proceso):
    r = proceso.registro
    inicial = r.activa()['version_id']
    proceso.reloj.adelantar(seconds=1)
    descartada = r.publicar_canario(PESOS_INICIALES, 30, {})
    assert r.volver_atras() == descartada
    proceso.reloj.adelantar(seconds=1)
    promovida = r.publicar_canario(PESOS_INICIALES, 30, {})
    r.muestra_minima = 0
    assert r.evaluar_canario() == 'promovido'
    assert r.activa()['version_id'] == promovida
    assert r.volver_atras() == inicial
    assert r.activa()['version_id'] == inicial


def test_entrenamiento_no_reinicia_canario(proceso):
    version = proceso.registro.publicar_canario(PESOS_INICIALES, 30, {})
    proceso.reloj.adelantar(days=1)
    assert proceso.entrenar()['entrenamiento']['resultado'] == 'esperando_canario'
    assert proceso.registro.canario()['version_id'] == version
