
# -*- encoding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (c) 2014 KIDDYS HOUSE SAC. (http://kiddyshouse.com).
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv import osv,fields
from openerp import netsvc
from openerp.tools.translate import _
import time

from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class stock_location(osv.osv):
    _name = 'stock.location'
    _inherit ='stock.location'
    _columns = {
        'bajo_pedido': fields.boolean('Despachos bajo pedidos de tienda',help="Marque esta opcion para permitir a las tiendas hacer despachos de esta ubicacion"), 
    }

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
        'sequencepos_id': fields.many2one('ir.sequence', "Secuencia orden venta TPV", help="La secuencia utilizada para las ordenes de venta de un TPV"),       
    }


class pos_order(osv.osv):
    _name = 'pos.order'
    _inherit ='pos.order'

    def write(self, cr, uid, ids, vals, context=None):
        res = super(pos_order, self).write(cr, uid, ids, vals, context=context)
        #If you change the partner of the PoS order, change also the partner of the associated bank statement lines
        partner_obj = self.pool.get('res.partner')
        bsl_obj = self.pool.get("account.bank.statement.line")
        if 'partner_id' in vals:
            for posorder in self.browse(cr, uid, ids, context=context):
                if posorder.invoice_id:
                    raise osv.except_osv( _('Error!'), _("You cannot change the partner of a POS order for which an invoice has already been issued."))
                if vals['partner_id']:
                    p_id = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
                    part_id = partner_obj._find_accounting_partner(p_id).id
                else:
                    part_id = False
                bsl_ids = [x.id for x in posorder.statement_ids]
                bsl_obj.write(cr, uid, bsl_ids, {'partner_id': part_id}, context=context)

        #Permite enviar el id del almacen de despacho al contexto
        
        if context is None:
            context = {}
        
        c = context.copy()
        for posorder in self.browse(cr, uid, ids, context=context):
            if posorder.almacendespacho_id:
                c.update({'location': posorder.almacendespacho_id.id })
                #_logger.error("CONTEXT _1: %r", c)
        #Fin

        for order in self.browse(cr, uid, ids, context=c):
            for line in order.lines:
                if  line.product_id.procedencia == 'import' and order.almacendespacho_id:
                    if line.product_id.qty_disponible < line.qty:
                        #_logger.error("PINCKING 1: %r", line.product_id.procedencia)
                        raise osv.except_osv(_('Warning!'),_('No puede vender un producto importado de almacen PRINCIPAL con stock insuficiente, Producto: "%s" (Cant. Dispo:%d).') %(line.product_id.name, line.product_id.qty_disponible,))
        #Fin     

        return res

    _columns = {
        'es_factura': fields.boolean('Facturada', states={'draft': [('readonly', False)],} ),
        'almacendespacho_id' : fields.many2one('stock.location', 'Almacen depacho', help="Ubicacion desde donde se despachara el producto al cliente, dejar en blanco si sale de la misma tienda", states={'draft': [('readonly', False)],} ),
        'doc_number': fields.char('RUC/DNI',size=32, states={'draft': [('readonly', False)],} ),
        'devolucion': fields.char('Devolucion de',size=64, states={'draft': [('readonly', False)],} ),
    }

    _defaults = {
        'es_factura': False,
    }

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        if not part:
            return {'value': {'doc_number':False,'es_factura': False}}
        #part = self.pool.get('res.partner').browse(cr, uid, part, context=context)

        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        doc_number = self.pool.get('res.partner').browse(cr, uid, part, context=context).doc_number
        if doc_number:
            if len(doc_number) == 11:
                return {'value': {'pricelist_id': pricelist, 'doc_number':doc_number, 'es_factura': True}}
        
        return {'value': {'pricelist_id': pricelist, 'doc_number':doc_number,'es_factura': False}}
    
    def onchange_ruc_dni(self, cr, uid, ids, ruc_dni, context=None):
        if context is None:
            context = {}
        value = {}
      
        partner_obj = self.pool.get('res.partner')
        if ruc_dni:
            partner_id = partner_obj.search(cr,uid,[('doc_number','=',ruc_dni)])
            if partner_id:
                value.update({
                       'partner_id': partner_id,
                    })
                return {'value': value}
            else:
                raise osv.except_osv(_('Warning!'), _('Usuario no registrado en el sistema.'))
        else:
            return {'value': {'pricelist_id': False, 'partner_id':False,'es_factura': False}}



    def create(self, cr, uid, values, context=None):

        #values['name'] = self.pool.get('ir.sequence').get(cr, uid, 'pos.order')

        pos_order_id = super(pos_order, self).create(cr, uid, values, context=context)
        #_logger.error("pos order ID 1: %r", pos_order_id)

        for order in self.browse(cr, uid, [pos_order_id], context=context):
            shop_id = order.shop_id
        #_logger.error("SHOP ID 0: %r", shop_id.id)
        shop = self.pool.get('sale.shop').browse(cr, uid, shop_id.id, context)
        sequence_obj = self.pool.get('ir.sequence')

        if shop and shop.sequencepos_id:
            values = {'name': sequence_obj.get_id(cr, uid, shop.sequencepos_id.id, context=context)}      
            self.write(cr, uid, [pos_order_id], values, context=context)

        if context is None:
            context = {}

        #Permite enviar el id del almacen de despacho al contexto
        c = context.copy()
        for posorder in self.browse(cr, uid, [pos_order_id], context=context):
            if posorder.almacendespacho_id:
                c.update({'location': posorder.almacendespacho_id.id })
                #_logger.error("CONTEXT _1: %r", c)
        #Fin

        for order in self.pool.get('pos.order').browse(cr, uid, [pos_order_id], context=c):
            for line in order.lines:
                #_logger.error("PINCKING 1: %r", order.lines)
                if  line.product_id.procedencia == 'import' and order.almacendespacho_id:
                    if line.product_id.qty_disponible < line.qty:
                        raise osv.except_osv(_('Warning!'),_('No puede vender un producto importado de almacen PRINCIPAL con stock insuficiente, Producto: "%s" (Cant. Dispo:%d).') %(line.product_id.name, line.product_id.qty_disponible,))
        #fin
        return pos_order_id

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking.out')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            if order.almacendespacho_id:
                if order.partner_id:
                    destination_id = order.partner_id.property_stock_customer.id 
                else:
                    destination_id = partner_obj.default_get(cr, uid, ['property_stock_customer'], context=context)['property_stock_customer']
                uid=1 
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery',False),
                    'type': 'in' if order.devolucion else 'out', 
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                    'auto_picking': False,
                    'location_id': order.almacendespacho_id.id,
                    'location_dest_id': destination_id,
                    'state': 'auto',
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
                location_id = order.almacendespacho_id.id           

                for line in order.lines:
                    if line.product_id and line.product_id.type == 'service':
                        continue
                    move_obj.create(cr, uid, {
                        'name': line.name,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uos': line.product_id.uom_id.id,
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'product_uos_qty': abs(line.qty),
                        'product_qty': abs(line.qty),
                        'tracking_id': False,
                        'type': 'in' if order.devolucion else 'out', 
                        'state': 'draft',
                        'location_id': location_id if line.qty >= 0 else destination_id,
                        'location_dest_id': destination_id if line.qty >= 0 else location_id,
                    }, context=context)
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
                #picking_obj.force_assign(cr, uid, [picking_id], context)
                picking_obj.action_assign(cr, uid, [picking_id], context)

                
            else:
                if order.partner_id:
                    destination_id = order.partner_id.property_stock_customer.id 
                else:
                    destination_id = partner_obj.default_get(cr, uid, ['property_stock_customer'], context=context)['property_stock_customer'] 

                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery',False),
                    'type': 'in' if order.devolucion else 'out', 
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                    'auto_picking': True,
                    'location_id': order.shop_id.warehouse_id.lot_stock_id.id if not order.devolucion else destination_id,
                    'location_dest_id': destination_id if not order.devolucion else order.shop_id.warehouse_id.lot_stock_id.id,
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
                location_id = order.shop_id.warehouse_id.lot_stock_id.id            

                for line in order.lines:
                    if line.product_id and line.product_id.type == 'service':
                        continue
                    move_obj.create(cr, uid, {
                        'name': line.name,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uos': line.product_id.uom_id.id,
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'product_uos_qty': abs(line.qty),
                        'product_qty': abs(line.qty),
                        'tracking_id': False,
                        'type': 'in' if order.devolucion else 'out', 
                        'state': 'draft',
                        'location_id': location_id if line.qty >= 0 else destination_id,
                        'location_dest_id': destination_id if line.qty >= 0 else location_id,
                    }, context=context)
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
                picking_obj.force_assign(cr, uid, [picking_id], context)

        return True

    def pos_print_report(self, cr, uid, ids, context=None):
        '''
        This function prints the invoice and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        self.write(cr, uid, ids, {'sent': True}, context=context)
        datas = {
             'ids': ids,
             'model': 'pos.order',
             'form': self.read(cr, uid, ids[0], context=context)
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'pos.order.print.ticket',
            'datas': datas,
            'nodestroy' : True
        }

pos_order()

class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _inherit = 'pos.order.line'
    _columns = {
        
    }
    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False, almacendespacho=False, context=None):
        context = context or {}

        #Permite enviar el id del almacen de despacho
        c = context.copy()
        if almacendespacho:
            c.update({'location': almacendespacho })
        #Fin

        if not product_id:
            return {}
        if not pricelist:
            raise osv.except_osv(_('No Pricelist!'),_('You have to select a pricelist in the sale form !\n' \
               'Please set one before choosing a product.'))

        #PERMITE VER SI LA CANTIDAD A VENDER ES PERMITIDA PARA PRODUCTOS IMPORTADOS
        prod_id = self.pool.get('product.product').browse(cr, uid, product_id, context=c) 
        #_logger.error("PINCK_CONTEXT1: %r", c)         
        if prod_id.procedencia == 'import' and almacendespacho:
            if prod_id.qty_disponible < qty:
                raise osv.except_osv(_('Warning!'),_('No puede vender un producto importado del almacen PRINCIPAL con stock insuficiente, Producto: "%s" (Cant. Dispo:%d).') %(prod_id.name, prod_id.qty_disponible,))
        #FIN        

        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],product_id, qty or 1.0, partner_id)[pricelist]
        result = self.onchange_qty(cr, uid, ids, product_id, 0.0, qty, price, context=c)
        result['value']['price_unit'] = price
        return result


    def onchange_qty(self, cr, uid, ids, product, discount, qty, price_unit, almacendespacho=False, context=None):
        result = {}

        #Permite enviar el id del almacen de despacho
        c = context.copy()
        if almacendespacho:
            c.update({'location': almacendespacho })
        #Fin

        if not product:
            return result
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')

        prod = self.pool.get('product.product').browse(cr, uid, product, context=c)

        price = price_unit * (1 - (discount or 0.0) / 100.0)
        taxes = account_tax_obj.compute_all(cr, uid, prod.taxes_id, price, qty, product=prod, partner=False)

        result['price_subtotal'] = taxes['total']
        result['price_subtotal_incl'] = taxes['total_included']

        #PERMITE VER SI LA CANTIDAD A VENDER ES PERMITIDA PARA PRODUCTOS IMPORTADOS
        #_logger.error("PINCK_CONTEXT2: %r", almacendespacho)

        if prod.procedencia == 'import':
            if prod.qty_disponible < qty and almacendespacho:
                raise osv.except_osv(_('Warning!'),_('Esta intentando vender un producto importado del almacen PRINCIPAL en una cantidad mayor a la cant. disponible, Producto: "%s" (Cant. Dispo:%d).') %(prod.name, prod.qty_disponible,))
        #FIN

        return {'value': result}


