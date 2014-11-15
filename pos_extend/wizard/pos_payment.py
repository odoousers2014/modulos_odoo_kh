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


import time

from openerp import netsvc
from openerp.osv import osv, fields
from openerp.tools.translate import _



class pos_make_payment_line(osv.TransientModel):
    _name = 'pos.make.payment.line'
    _columns = {
        'journal_id' : fields.many2one('account.journal', 'Diario', required=True),
        'statement_id': fields.many2one('account.bank.statement', 'Extracto', required=False),
        'amount': fields.float('Importe', digits=(16,2), required= True),
        'wizard_id': fields.many2one('pos.make.payment', 'Wizard', ondelete='CASCADE'),
    }

pos_make_payment_line()


class pos_make_payment(osv.osv_memory):
    _inherit = 'pos.make.payment'
#    _rec_name = 'order_id'
    _columns = {
        'statement_ids': fields.one2many('pos.make.payment.line', 'wizard_id', 'Payments', readonly=False),
        'order_id' :  fields.many2one('pos.order', "Order", ondelete='CASCADE'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(pos_make_payment, self).default_get(cr, uid, fields, context=context)
        order_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        #if not picking_ids or len(picking_ids) != 1:
            ## Partial Picking Processing may only be done for one picking at a time
        #    return res
        assert active_model in ('pos.order'), 'Bad context propagation'
        order_id, = order_ids
        if 'order_id' in fields:
            res.update(order_id=order_id)
        if 'statement_ids' in fields:
            order = self.pool.get('pos.order').browse(cr, uid, order_id, context=context)
            moves = [self._partial_move_for(cr, uid, m) for m in order.statement_ids ]
            res.update(statement_ids=moves)

        return res

    def _partial_move_for(self, cr, uid, move):
        partial_move = {
            'journal_id' : move.journal_id.id,
            'statement_id' : move.statement_id.id,
            'amount': move.amount,
        }
        return partial_move

pos_make_payment()
