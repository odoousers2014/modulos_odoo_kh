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
from openerp import tools
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class stock_location(osv.osv):
    _name = "stock.location"
    _inherit ='stock.location'
    _columns = {
            'sequence_in_id': fields.many2one('ir.sequence','Secuencia ingreso',help='Secuencia de picking de ingreso a esta ubicacion p.e: ING01-001'),
            'sequence_int_id': fields.many2one('ir.sequence','Secuencia interno',help='Secuencia de picking para traslado internos entre ubicaciones de la empresa p.e: MOV01-001'),
            'sequence_out_id': fields.many2one('ir.sequence','Secuencia salida',help='Secuencia de picking de despacho de esta ubicacion a clientes p.e: SAL01-001'),
            'user_ids': fields.many2many('res.users', 'stock_location_user_rel', 'user_id', 'location_id', "Users"),
    #       'group_ids': fields.many2many('res.groups', 'stock_journal_rel', 'sequence_id', 'groups_id', 'Groups'),
    }


stock_location()

class users(osv.osv):
    _inherit  =  "res.users"
    _columns  =  {
        'location_ids': fields.many2many('stock.location', 'stock_location_user_rel', 'location_id', 'user_id', "Locations"),
    }

    def __init__(self, *args):
        super(users, self).__init__(*args)
        if 'location_id' not in self.SELF_WRITEABLE_FIELDS:
            self.SELF_WRITEABLE_FIELDS.append('location_id')

users()

class stock_picking(osv.osv):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        picking_obj = self.browse(cr, uid, id, context=context)
        if ('name' not in default) or (picking_obj.name == '/'):
            seq_obj_name = 'stock.picking.' + picking_obj.type
            #default['name'] = self.pool.get('ir.sequence').get(cr, uid, seq_obj_name)
            default['name'] = self.pool.get('ir.sequence').get_id(cr, uid, picking_obj.location_id.sequence_int_id.id)
            default['origin'] = ''
            default['date'] = time.strftime('%Y-%m-%d %H:%M:%S')
            default['backorder_id'] = False
        if 'invoice_state' not in default and picking_obj.invoice_state == 'invoiced':
            default['invoice_state'] = '2binvoiced'
        res = super(stock_picking, self).copy(cr, uid, id, default, context)
        return res

    def create(self, cr, uid, vals, context=None):# PARA SECUENCIAS POR UBICACIONES

        picking_id = super(stock_picking, self).create(cr, uid, vals, context=context)

        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        sequence_obj = self.pool.get('ir.sequence')

        #COMPRUEBA LAS CANTIDADES ANTES DE CONFIRMARUN PICKING FECHA 25/10/2014
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        for move in picking.move_lines:
            if context is None:
                context = {}                    
            c = context.copy()
            c.update({'location': move.location_id.id })
            product = self.pool.get('product.product').browse(cr, uid, [move.product_id.id], c)[0]
            #_logger.error("stcockmoveee----: %r", product.virtual_available)
            #if product.virtual_available < move.product_qty:
            if product.qty_available < move.product_qty and (product.type=='product'):
                raise osv.except_osv(_('Warning!'),_('Verifique su stock, no hay stock suficiente, Producto: "%s"') %(product.name))
        #FIN COMPRUEBA LAS CANTIDADES ANTES DE CONFIRMAR


        #if ('name' not in vals) or (vals.get('name')=='/'):
        if ('name' not in vals) and vals['type'] == 'internal':
            if ('do_partial' not in vals) or vals['do_partial'] == False:
            #if vals['do_partial'] == False:
                location_id = vals.get('location_id')
                if location_id:
                    location = self.pool.get('stock.location').browse(cr, uid, location_id, context)
                    if location.sequence_int_id:                    
                        vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_int_id.id, context=context)}
                        #_logger.error("PINCKING 1: %r", vals)

                        for move in picking.move_lines:
                            if move.location_id == move.location_dest_id:
                                raise osv.except_osv(_('Warning!'), _('La ubicacion de origen y destino no puede ser la misma en los movimientos')) 


                        self.write(cr, uid, picking_id, vals, context=context)
                    else:
                        raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tienes secuencia asignanda.'))
                else:
                    for move in picking.move_lines:
                        location_id = move.location_id

                        if move.location_id == move.location_dest_id:
                            raise osv.except_osv(_('Warning!'), _('La ubicacion de origen y destino no puede ser la misma en los movimientos')) 

                        location = self.pool.get('stock.location').browse(cr, uid, location_id.id, context)
                        if location.sequence_int_id: 
                            vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_int_id.id, context=context)}
                            #_logger.error("PINCKING 2: %r", vals)
                            self.write(cr, uid, picking_id, vals, context=context)
                        else:
                            raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tiene secuencia asignanda.'))   
                

        if picking.sale_purchase_origin:
            if vals['type'] == 'in':
                if ('do_partial' not in vals):       
                    location_id = vals.get('location_dest_id', [])
                    if location_id:
                        location = self.pool.get('stock.location').browse(cr, uid, location_id, context)
                        if location.sequence_in_id:
                            vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_in_id.id, context=context)}
                            self.write(cr, uid, picking_id, vals, context=context)
                        else:
                            raise osv.except_osv(_('Warning!'), _('Ubicacion de destino no tiene secuencia asignanda.'))
                    else:
                        for move in picking.move_lines:
                            location_id = move.location_dest_id        
                            location = self.pool.get('stock.location').browse(cr, uid, location_id.id, context)
                            if location.sequence_in_id:
                                vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_in_id.id, context=context)}
                                self.write(cr, uid, picking_id, vals, context=context)
                            else:
                                raise osv.except_osv(_('Warning!'), _('Ubicacion de destino no tiene secuencia asignanda.'))                         

            else:
                if ('do_partial' not in vals):
                    location_id = vals.get('location_id', [])
                    if location_id:
                        location = self.pool.get('stock.location').browse(cr, uid, location_id, context)
                        if location.sequence_out_id:
                            vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_out_id.id, context=context)}
                            self.write(cr, uid, picking_id, vals, context=context)
                        else:
                            raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tiene secuencia asignanda.'))
                    else:
                        for move in picking.move_lines:
                            location_id = move.location_id        
                            location = self.pool.get('stock.location').browse(cr, uid, location_id.id, context)
                            if location.sequence_out_id:
                                vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_out_id.id, context=context)}
                                self.write(cr, uid, picking_id, vals, context=context)
                            else:
                                raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tiene secuencia asignanda.'))
                    
                  
        return picking_id

    _columns  =  {
        'sale_purchase_origin': fields.boolean('Origen de compra o venta'),
        'do_partial': fields.boolean('Do partial'),
    }

    def do_partial(self, cr, uid, ids, partial_datas, context=None): # PARA ENTRGAS PARCIALES

        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                
                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id not in product_avail:
                        # keep track of stock on hand including processed lines not yet marked as done
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency, move_currency_id, product_price, round=False)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price, product.uom_id.id)
                        if product_avail[product.id] <= 0:
                            product_avail[product.id] = 0
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id]) + (new_price * qty))/(product_avail[product.id] + qty)
                        
                        # Write the field according to price type field
                        #SE COMENTO PARA EVITAR VALORIZAR CUANDO SE RECIBE EL PRODUCTO EN EL ALMCEN

                        ##product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id], {'price_unit': product_price, 'price_currency_id': product_currency})

                        product_avail[product.id] += qty

            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:

                    new_picking_name = pick.name
                    #AGREGADO AL METODO ORIGINAL PARA ENTREGAS PARCIALES
                    if pick.type == 'internal':
                        if pick.location_id:
                            new_sequence_name = sequence_obj.get_id(cr, uid, pick.location_id.sequence_int_id.id)
                            self.write(cr, uid, [pick.id], {'name': new_sequence_name,})
                            new_picking = self.copy(cr, uid, pick.id, {'name': new_picking_name,'do_partial': True,'move_lines' : [],'state':'draft',},)
                        else:
                            raise osv.except_osv(_('Warning!'), _('Elija una ubicacion de origen y destino.'))
                    if pick.type == 'out':
                        if pick.location_id:
                            new_sequence_name = sequence_obj.get_id(cr, uid, pick.location_id.sequence_out_id.id)
                            self.write(cr, uid, [pick.id], {'name': new_sequence_name,})
                            new_picking = self.copy(cr, uid, pick.id, {'name': new_picking_name,'do_partial': True,'move_lines' : [],'state':'draft',}) 
                        else:
                            raise osv.except_osv(_('Warning!'), _('Elija por lo menos la ubicacion de origen en la guia..'))

                    if pick.type == 'in':
                        if pick.location_dest_id:
                            new_sequence_name = sequence_obj.get_id(cr, uid, pick.location_dest_id.sequence_in_id.id)
                            self.write(cr, uid, [pick.id], {'name': new_sequence_name,})
                            new_picking = self.copy(cr, uid, pick.id, {'name': new_picking_name,'do_partial': True,'move_lines' : [],'state':'draft',})            
                        else:
                            raise osv.except_osv(_('Warning!'), _('Elija por lo menos la ubicacion de destino en la guia.'))
                    #FIN        

                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = pick.id
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, new_picking, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def action_cancel(self, cr, uid, ids, context=None):
        """ Changes picking state to cancel.
        @return: True
        """
        move_obj = self.pool.get('stock.move')

        #inicio cambios
        picking_obj= self.pool.get('stock.picking')
        date = None
        sale= None
        pick_name=None
        for pick in self.browse(cr, uid, ids, context=context):
            date=pick.date
            sale = pick.sale_id
            pick_name = pick.name
        if not sale: 
            uid=1
            pick_ids=picking_obj.search(cr, uid,[('date','=',date),('name','=',pick_name),], order='date')          
            #_logger.error("stock IDDDD----: %r", pick_ids)
            for picks in picking_obj.browse(cr, uid, pick_ids):
                if picks.state in ('draft', 'assigned','confirmed'):
                    #_logger.error("IDDDD----: %r", ids)
                    ids2 = [move.id for move in picks.move_lines]
                    move_obj.action_cancel(cr, uid, ids2, context)
                    self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        #fin cambios 
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            move_obj.action_cancel(cr, uid, ids2, context)
        self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        return True

class stock_picking_in(osv.osv):
    _name = "stock.picking.in"
    _inherit = "stock.picking.in"
    _table = "stock_picking"
    _description = "Delivery Orders"

    def create(self, cr, uid, vals, context=None): # PARA SECUENCIAS POR UBICACIONES

        picking_id = super(stock_picking_in, self).create(cr, uid, vals, context=context)
        #_logger.error("PINCKING id1: %r", picking_id)
        picking = self.pool.get('stock.picking.in').browse(cr, uid, picking_id, context=context)
        sequence_obj = self.pool.get('ir.sequence')
        
        #if ('name' not in vals) or (vals.get('name')=='/'):
        if vals['type'] == 'in':           
            location_id = vals.get('location_dest_id', [])
            if location_id:
                location = self.pool.get('stock.location').browse(cr, uid, location_id, context)
                if location.sequence_in_id:
                    vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_in_id.id, context=context)}
                    self.write(cr, uid, picking_id, vals, context=context)            
                else:
                    raise osv.except_osv(_('Warning!'), _('Ubicacion de destino no tiene secuencia asignanda.'))
            else:
                for move in picking.move_lines:
                    location_id = move.location_dest_id        
                    location = self.pool.get('stock.location').browse(cr, uid, location_id.id, context)
                    if location.sequence_in_id:
                        vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_in_id.id, context=context)}
                        self.write(cr, uid, picking_id, vals, context=context)
                        
                    else:
                        raise osv.except_osv(_('Warning!'), _('Ubicacion de destino no tiene secuencia asignanda.'))
            
        return picking_id

class stock_picking_out(osv.osv):
    _name = "stock.picking.out"
    _inherit = "stock.picking.out"
    _table = "stock_picking"
    _description = "Delivery Orders"

    def create(self, cr, uid, vals, context=None): # PARA SECUENCIAS POR UBICACIONES

        picking_id = super(stock_picking_out, self).create(cr, uid, vals, context=context)
        picking = self.pool.get('stock.picking.out').browse(cr, uid, picking_id, context=context)
        sequence_obj = self.pool.get('ir.sequence')
        #_logger.error("PINCKING: %r", picking)
        #if ('name' not in vals) or (vals.get('name')=='/'):
        if vals['type'] == 'out':
            location_id = vals.get('location_id', [])
            if location_id:
                location = self.pool.get('stock.location').browse(cr, uid, location_id, context)
                if location.sequence_out_id:
                    vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_out_id.id, context=context)}
                    self.write(cr, uid, picking_id, vals, context=context)
                else:
                    raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tiene secuencia asignanda.'))
            else:
                for move in picking.move_lines:
                    location_id = move.location_id        
                    location = self.pool.get('stock.location').browse(cr, uid, location_id.id, context)
                    if location.sequence_out_id:
                        vals = {'name': sequence_obj.get_id(cr, uid, location.sequence_out_id.id, context=context)}
                        self.write(cr, uid, picking_id, vals, context=context)
                    else:
                        raise osv.except_osv(_('Warning!'), _('Ubicacion de origen no tiene secuencia asignanda.'))
        
        return picking_id


class stock_move(osv.osv):
    _name = "stock.move"
    _inherit = 'stock.move'


    def _prepare_chained_picking(self, cr, uid, picking_name, new_location_id, new_location_dest_id, picking, picking_type, moves_todo, context=None):
            """Prepare the definition (values) to create a new chained picking.

               :param str picking_name: desired new picking name
               :param browse_record picking: source picking (being chained to)
               :param str picking_type: desired new picking type
               :param list moves_todo: specification of the stock moves to be later included in this
                   picking, in the form::

                       [[move, (dest_location, auto_packing, chained_delay, chained_journal,
                                      chained_company_id, chained_picking_type)],
                        ...
                       ]

                   See also :meth:`stock_location.chained_location_get`.
            """
            res_company = self.pool.get('res.company')

            if new_location_id == new_location_dest_id:
                raise osv.except_osv(_('Warning!'), _('La ubicacion de origen y destino no puede ser la misma en los movimientos de stock')) 

            return {
                        'name': picking_name,
                        'location_id': new_location_id, #Para transito
                        'location_dest_id' : new_location_dest_id , #Para transito
                        'origin': tools.ustr(picking.origin or ''),
                        'type': picking_type,
                        'note': picking.note,
                        'move_type': picking.move_type,
                        'auto_picking': moves_todo[0][1][1] == 'auto',
                        'stock_journal_id': moves_todo[0][1][3],
                        'company_id': moves_todo[0][1][4] or res_company._company_default_get(cr, uid, 'stock.company', context=context),
                        'partner_id': picking.partner_id.id,
                        'invoice_state': 'none',
                        'date': picking.date,
                    }

    def _create_chained_picking(self, cr, uid, picking_name, new_location_id, new_location_dest_id, picking, picking_type, moves_todo, context=None):
        picking_obj = self.pool.get('stock.picking')
        return picking_obj.create(cr, uid, self._prepare_chained_picking(cr, uid, picking_name, new_location_id, new_location_dest_id, picking, picking_type, moves_todo, context=context))


    def create_chained_picking(self, cr, uid, moves, context=None): 
        res_obj = self.pool.get('res.company')
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        new_moves = []
        if context is None:
            context = {}
        seq_obj = self.pool.get('ir.sequence')
        for picking, todo in self._chain_compute(cr, uid, moves, context=context).items():
            ptype = todo[0][1][5] and todo[0][1][5] or location_obj.picking_type_get(cr, uid, todo[0][0].location_dest_id, todo[0][1][0])
            if picking:
                # name of new picking according to its type
                if ptype == 'internal':
                    #new_pick_name = seq_obj.get(cr, uid,'stock.picking')
                    new_pick_name = picking.name # PARA ZONAS DE TRANSITO
                    new_location_id = picking.location_dest_id.id # PARA ZONAS DE TRANSITO
                    new_location_dest_id = picking.location_dest_id.chained_location_id.id,
                    #_logger.error("PINCKING ddddddddd: %r", new_location_dest_id)
                else :
                    new_pick_name = seq_obj.get(cr, uid, 'stock.picking.' + ptype)
                pickid = self._create_chained_picking(cr, uid, new_pick_name, new_location_id, new_location_dest_id, picking, ptype, todo, context=context)
                # Need to check name of old picking because it always considers picking as "OUT" when created from Sales Order
                old_ptype = location_obj.picking_type_get(cr, uid, picking.move_lines[0].location_id, picking.move_lines[0].location_dest_id)
                if old_ptype != picking.type:
                    old_pick_name = seq_obj.get(cr, uid, 'stock.picking.' + old_ptype)
                    self.pool.get('stock.picking').write(cr, uid, [picking.id], {'name': old_pick_name, 'type': old_ptype, }, context=context)
            else:
                pickid = False
            for move, (loc, dummy, delay, dummy, company_id, ptype, invoice_state) in todo:
                new_id = move_obj.copy(cr, uid, move.id, {
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': loc.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'picking_id': pickid,
                    'state': 'waiting',
                    'company_id': company_id or res_obj._company_default_get(cr, uid, 'stock.company', context=context)  ,
                    'move_history_ids': [],
                    'date_expected': (datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S') + relativedelta(days=delay or 0)).strftime('%Y-%m-%d'),
                    'move_history_ids2': []}
                )
                move_obj.write(cr, uid, [move.id], {
                    'move_dest_id': new_id,
                    'move_history_ids': [(4, new_id)]
                })
                new_moves.append(self.browse(cr, uid, [new_id])[0])
            if pickid:
                wf_service.trg_validate(uid, 'stock.picking', pickid, 'button_confirm', cr)
        if new_moves:
            new_moves += self.create_chained_picking(cr, uid, new_moves, context)
        return new_moves

    #
    # Duplicate stock.move
    #
    def check_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        @return: No. of moves done
        """
        done = []
        count = 0
        pickings = {}
        if context is None:
            context = {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.product_id.type == 'consu' or move.location_id.usage == 'supplier':
                if move.state in ('confirmed', 'waiting'):
                    done.append(move.id)
                pickings[move.picking_id.id] = 1
                continue
            if move.state in ('confirmed', 'waiting'):
                # Important: we must pass lock=True to _product_reserve() to avoid race conditions and double reservations
                res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id, move.product_qty, {'uom': move.product_uom.id}, lock=True)
                if res:
                    #_product_available_test depends on the next status for correct functioning
                    #the test does not work correctly if the same product occurs multiple times
                    #in the same order. This is e.g. the case when using the button 'split in two' of
                    #the stock outgoing form
                    self.write(cr, uid, [move.id], {'state':'assigned'})
                    done.append(move.id)
                    pickings[move.picking_id.id] = 1
                    r = res.pop(0)
                    product_uos_qty = self.pool.get('stock.move').onchange_quantity(cr, uid, [move.id], move.product_id.id, r[0], move.product_id.uom_id.id, move.product_id.uos_id.id)['value']['product_uos_qty']
                    cr.execute('update stock_move set location_id=%s, product_qty=%s, product_uos_qty=%s where id=%s', (r[1], r[0],product_uos_qty, move.id))

                    while res:
                        r = res.pop(0)
                        product_uos_qty = self.pool.get('stock.move').onchange_quantity(cr, uid, [move.id], move.product_id.id, r[0], move.product_id.uom_id.id, move.product_id.uos_id.id)['value']['product_uos_qty']
                        move_id = self.copy(cr, uid, move.id, {'product_uos_qty': product_uos_qty, 'product_qty': r[0], 'location_id': r[1]})
                        done.append(move_id)
                else:
                    raise osv.except_osv(_('Warning!'),_('Verifique su stock, no hay stock suficiente, Producto: "%s"') %(move.product_id.name))          

        if done:
            count += len(done)
            self.write(cr, uid, done, {'state': 'assigned'})

        if count:
            for pick_id in pickings:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
        return count

stock_move()


class sale_order(osv.osv):
    _name = 'sale.order'
    _inherit = "sale.order"

    def _prepare_order_picking(self, cr, uid, order, context=None):
        #pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        return {
            #'name': pick_name,
            #'name': '/',
            'origin': order.name,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
            'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
            #'location_dest_id' : order.shop_id.warehouse_id.lot_output_id.id,
            'location_dest_id' : order.partner_id.property_stock_customer.id,
            'sale_purchase_origin': True,
        }

    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.type in ('product', 'consu'):
                    if not picking_id:
                        #PARA PEDIDOS DEL ALMACEN PRINCIPAL
                        if order.shop_id.warehouse_id.lot_stock_id.id == 12 : 
                            uid=1 
                        #FIN
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                    move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
                else:
                    # a service has no stock move
                    move_id = False

                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")

        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            #picking_obj.action_assign(cr, uid, [picking_id], context) #PARA CUANDO DE EJECUTE EL PICKING Y PASE A ESTADO RESERVADO AUTOMATICAMENTE
        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True


sale_order()

class purchase_order(osv.osv):
    _name='purchase.order'
    _inherit='purchase.order'

    def _prepare_order_picking(self, cr, uid, order, context=None):
        return {
            #'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
            #'name': '/',
            'origin': order.name + ((order.origin and (':' + order.origin)) or ''),
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'partner_id': order.partner_id.id,
            'invoice_state': '2binvoiced' if order.invoice_method == 'picking' else 'none',
            'type': 'in',
            'purchase_id': order.id,
            'company_id': order.company_id.id,
            'move_lines' : [],
            'location_id' : order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'sale_purchase_origin': True,
        }
    #PARA VALORIZAR EL PRODUCTO SI EN EL PRECIO UNIT ESTA CON IGV INCLIUDO
    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):        
        price_unit = 0.0
        #for c in self.pool.get('account.tax').compute_all(cr, uid, order_line.taxes_id, order_line.price_unit, order_line.product_qty, order_line.product_id, order.partner_id)['taxes']:           
        for tax in order_line.taxes_id:
            if tax.price_include:
                price_unit = (order_line.price_unit/(1 + tax.amount))
            else:
                price_unit = order_line.price_unit
        if not order_line.taxes_id:
            price_unit = order_line.price_unit
        #_logger.error("PURCHA1----: %r", price_unit)


        return {
            'name': order_line.name or '',
            'product_id': order_line.product_id.id,
            'product_qty': order_line.product_qty,
            'product_uos_qty': order_line.product_qty,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'date_expected': self.date_to_datetime(cr, uid, order_line.date_planned, context),
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': order_line.move_dest_id.id,
            'state': 'draft',
            'type':'in',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            #'price_unit': order_line.price_unit
            #'price_unit': (order_line.price_unit*order_line.product_qty-val)/order_line.product_qty
            'price_unit': price_unit
        }

purchase_order()

