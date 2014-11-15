# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) KIDDYS HOUSE S.A.C (<http://kiddyshouse.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name" : "Sale order date expected",
    "version" : "1.0",
    "depends" : ['base','sale'],  
    "author" : "OpenERP SA",
    "description": """
        Este modulo agrega echa para la planificacion de entrega del producto al Cliente en el pedido de venta
    """,
    "website" : "http://www.salazarcarlos.com",
    "category" : "",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "sale_view.xml",
    ],
    "active": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: