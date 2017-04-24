from sam import common
import re
from sam import errors
import base
import sam.models.details
import sam.models.nodes
import sam.models.links


# This class is for getting the main selection details, such as ins, outs, and ports.


def nice_protocol(p_in, p_out):
    """
    
    :param p_in: comma-seperated protocol list for inbound connections
     :type p_in: unicode
    :param p_out: comma-seperated protocol list for outbound connections
     :type p_out: unicode
    :return: user-friendly string describing in-/outbound connections
     :rtype: unicode
    """
    pin = p_in.split(u',') if p_in else []
    pout = p_out.split(u',') if p_out else []
    protocols = set(pin) | set(pout)
    protocols.discard(u'')
    ins = []
    outs = []
    both = []
    for p in protocols:
        if p in pin and p in pout:
            both.append(u'{} (i/o)'.format(p))
        elif p in pin:
            ins.append(u'{} (in)'.format(p))
        else:
            outs.append(u'{} (out)'.format(p))
    return u', '.join(ins+both+outs)


def si_formatting(f, places=2):
    """
    :param f: real number, the value to express
     :type f: float 
    :param places: number of decimal places to keep
     :type places: int
    :return: string with K/M/G postfix
    :rtype: unicode
    """
    format_string = u'{{val:.{places}f}}{{prefix}}'.format(places=places)
    f = float(f)
    if f < 1000:
        return format_string.format(val=f, prefix=u'')
    f /= 1000
    if f < 1000:
        return format_string.format(val=f, prefix=u'K')
    f /= 1000
    if f < 1000:
        return format_string.format(val=f, prefix=u'M')
    f /= 1000
    return format_string.format(val=f, prefix=u'G')


class Details(base.Headless):
    """
    The expected GET data includes:
        'address': dotted-decimal IP addresses.
            Each address is only as long as the subnet,
                so 12.34.0.0/16 would be written as 12.34
        'ds': string, specify the data source, ex: "ds_19_"
        'tstart': optional. Used with 'tend'. The start of the time range to report links during.
        'tend': optional. Used with 'tstart'. The end of the time range to report links during.
    :return: A JSON-encoded dictionary where
        the keys are ['conn_in', 'conn_out', 'ports_in', 'unique_in', 'unique_out', 'unique_ports'] and
        the values are numbers or lists
    """
    default_page = 1
    default_page_size = 50

    def __init__(self):
        base.Headless.__init__(self)
        # self.ip_range = (0, 4294967295)
        self.page_size = Details.default_page_size
        self.detailsModel = None
        self.nodesModel = sam.models.nodes.Nodes(common.db, self.user.viewing)
        self.linksModel = None  # set during decode_get_request()

    def decode_get_request(self, data):
        # data source
        if "ds" in data:
            ds_match = re.search("(\d+)", data['ds'])
            if ds_match:
                ds = int(ds_match.group())
            else:
                raise errors.MalformedRequest("Could not read data source ('ds')")
        else:
            raise errors.RequiredKey('data source', 'ds')
        self.linksModel = sam.models.links.Links(common.db, self.user.viewing, ds)
        # port filter
        port = data.get('port')

        # time range
        try:
            tstart = int(data.get('tstart'))
            tend = int(data.get('tend'))
        except ValueError:
            raise errors.MalformedRequest("Time range ({0} .. {1}) cannot be read. Check formatting"
                                          .format(data.get('tstart'), data.get('tend')))
        except (KeyError, TypeError):
            t_range = self.linksModel.get_timerange()
            tstart = t_range['min']
            tend = t_range['max']

        # address
        address = data.get('address')
        if not address:
            raise errors.RequiredKey('address', 'address')

        # pagination
        try:
            page = int(data.get('page', self.default_page))
        except ValueError:
            raise errors.MalformedRequest("Could not read page number: {0}".format(data.get('page')))
        try:
            page_size = int(data.get('page_size', self.default_page_size))
        except ValueError:
            raise errors.MalformedRequest("Could not read page size: {0}".format(data.get('page_size')))

        order = data.get('order')
        simple = data.get('simple', False) == "true"
        components = data.get('component', [])
        if components:
            components = components.split(',')

        self.page_size = page_size
        print("---")
        print("Creating details model with ds {}".format(ds))
        print("---")
        self.detailsModel = sam.models.details.Details(common.db, self.user.viewing, ds, address, (tstart, tend), port, page_size)

        request = {
            'ds': ds,
            'address': address,
            'page': page,
            'page_size': page_size,
            'order': order,
            'simple': simple,
            'components': components,
            'time_range': (tstart, tend)
        }
        return request

    def perform_get_command(self, request):
        """
            request = {
                'ds': ds,
                'address': ips "10.20",
                'page': page,
                'page_size': page_size,
                'order': order,
                'simple': simple,
                'components': components,
                'time_range': (tstart, tend)
            }
        :param request:
        :return:
        """
        self.require_group('read')
        details = {}
        if request['components']:
            for c_name in request['components']:
                if c_name == 'quick_info':
                    details[c_name] = self.quick_info(request['address'])
                elif c_name == 'inputs':
                    details[c_name] = self.inputs(request['page'],
                                                  request['order'],
                                                  request['simple'])
                elif c_name == 'outputs':
                    details[c_name] = self.outputs(request['page'],
                                                   request['order'],
                                                   request['simple'])
                elif c_name == 'ports':
                    details[c_name] = self.ports(request['page'],
                                                 request['order'])
                elif c_name == 'children':
                    details[c_name] = self.children(request['page'],
                                                    request['order'])
                elif c_name == 'summary':
                    details[c_name] = self.summary()
                else:
                    details[c_name] = {"result": "No data source matches request for {0}".format(c_name)}
        else:
            details = self.selection_info(request['page'], request['order'], request['simple'])

        return details

    def encode_get_response(self, response):
        return response

    @staticmethod
    def nice_ip_address(address):
        ip_start, ip_end = common.determine_range_string(address)
        subnet = 32 - (ip_end - ip_start).bit_length()
        return "{0}/{1}".format(common.IPtoString(ip_start), subnet)

    def quick_info(self, address):
        info = {}
        node_info = self.detailsModel.get_metadata()

        info['address'] = self.nice_ip_address(address)
        
        if node_info:
            tags = self.nodesModel.get_tags(address)
            envs = self.nodesModel.get_env(address)
            # node_info has:
            # hostname
            # unique_out_ip
            # unique_out_conn
            # overall_bps
            # total_out
            # out_bytes_sent
            # out_bytes_received
            # out_packets_sent
            # out_packets_received
            # unique_in_ip
            # unique_in_conn
            # total_in
            # in_bytes_sent
            # in_bytes_received
            # in_packets_sent
            # in_packets_received
            # ports_used
            # endpoints
            # seconds
            info['name'] = node_info.hostname
            info['tags'] = tags
            info['envs'] = envs
            info['protocols'] = nice_protocol(node_info.in_protocols, node_info.out_protocols)
            info['bps'] = node_info.overall_bps
            info['in'] = {}
            info['in']['total'] = node_info.total_in
            info['in']['u_ip'] = node_info.unique_in_ip
            info['in']['u_conn'] = node_info.unique_in_conn
            info['in']['seconds'] = node_info.seconds
            if not node_info.in_bytes_sent and not node_info.in_bytes_received:
                info['in']['bytes_sent'] = 0
                info['in']['bytes_received'] = 0
            else:
                info['in']['bytes_sent'] = node_info.in_bytes_sent
                info['in']['bytes_received'] = node_info.in_bytes_received
            info['in']['max_bps'] = node_info.in_max_bps if node_info.in_max_bps else 0
            info['in']['avg_bps'] = node_info.in_avg_bps if node_info.in_avg_bps else 0
            if not node_info.in_packets_sent and not node_info.in_packets_received:
                info['in']['packets_sent'] = 0
                info['in']['packets_received'] = 0
            else:
                info['in']['packets_sent'] = node_info.in_packets_sent
                info['in']['packets_received'] = node_info.in_packets_received
            info['in']['duration'] = node_info.in_duration
            info['out'] = {}
            info['out']['total'] = node_info.total_out
            info['out']['u_ip'] = node_info.unique_out_ip
            info['out']['u_conn'] = node_info.unique_out_conn
            info['out']['seconds'] = node_info.seconds
            if not node_info.out_bytes_sent and not node_info.out_bytes_received:
                info['out']['bytes_sent'] = 0
                info['out']['bytes_received'] = 0
            else:
                info['out']['bytes_sent'] = node_info.out_bytes_sent
                info['out']['bytes_received'] = node_info.out_bytes_received
            info['out']['max_bps'] = node_info.out_max_bps if node_info.out_max_bps else 0
            info['out']['avg_bps'] = node_info.out_avg_bps if node_info.out_avg_bps else 0
            if not node_info.out_packets_sent and not node_info.out_packets_received:
                info['out']['packets_sent'] = 0
                info['out']['packets_received'] = 0
            else:
                info['out']['packets_sent'] = node_info.out_packets_sent
                info['out']['packets_received'] = node_info.out_packets_received
            info['out']['duration'] = node_info.out_duration
            info['role'] = float(node_info.total_in / max(1, (node_info.total_in + node_info.total_out)))
            info['ports'] = node_info.ports_used
            info['endpoints'] = int(node_info.endpoints)
        else:
            info['error'] = 'No host found this address'
        return info

    def inputs(self, page, order, simple):
        inputs = self.detailsModel.get_details_connections(inbound=True, page=page, order=order, simple=simple)
        if simple:
            headers = [
                ['src', "Source IP"],
                ['port', "Dest. Port"],
                ['links', 'Count / min']
            ]
        else:
            headers = [
                ['src', "Source IP"],
                ['dst', "Dest. IP"],
                ['port', "Dest. Port"],
                ['links', 'Count / min'],
                # ['protocols', 'Protocols'],
                ['sum_bytes', 'Sum Bytes'],
                # ['avg_bytes', 'Avg Bytes'],
                ['sum_packets', 'Sum Packets'],
                # ['avg_packets', 'Avg Packets'],
                ['avg_duration', 'Avg Duration'],
            ]
        # convert list of dicts to ordered list of values
        minutes = float(self.request['time_range'][1] - self.request['time_range'][0]) / 60.0
        minutes = max(minutes, 1.0)
        conn_in = []
        for row in inputs:
            conn_row = []
            for h in headers:
                if h[0] == 'links':
                    conn_row.append(si_formatting(float(row['links']) / minutes))
                else:
                    conn_row.append(row[h[0]])
            conn_in.append(conn_row)
        response = {
            "page": page,
            "page_size": self.request['page_size'],
            "order": order,
            "direction": "desc",
            "component": "inputs",
            "headers": headers,
            "rows": conn_in
        }
        return response

    def outputs(self, page, order, simple):
        outputs = self.detailsModel.get_details_connections(inbound=False, page=page, order=order, simple=simple)

        if simple:
            headers = [
                ['dst', "Dest. IP"],
                ['port', "Dest. Port"],
                ['links', 'Count / min']
            ]
        else:
            headers = [
                ['src', "Source IP"],
                ['dst', "Dest. IP"],
                ['port', "Dest. Port"],
                ['links', 'Count / min'],
                # ['protocols', 'Protocols'],
                ['sum_bytes', 'Sum Bytes'],
                # ['avg_bytes', 'Avg Bytes'],
                ['sum_packets', 'Sum Packets'],
                # ['avg_packets', 'Avg Packets'],
                ['avg_duration', 'Avg Duration'],
            ]
        minutes = float(self.request['time_range'][1] - self.request['time_range'][0]) / 60.0
        minutes = max(minutes, 1.0)
        conn_out = []
        for row in outputs:
            conn_row = []
            for h in headers:
                if h[0] == 'links':
                    conn_row.append(si_formatting(float(row['links']) / minutes))
                else:
                    conn_row.append(row[h[0]])
            conn_out.append(conn_row)
        response = {
            "page": page,
            "page_size": self.request['page_size'],
            "order": order,
            "direction": "desc",
            "component": "outputs",
            "headers": headers,
            "rows": conn_out
        }
        return response

    def ports(self, page, order):
        ports = self.detailsModel.get_details_ports(page, order)

        headers = [
            ['port', "Port Accessed"],
            ['links', 'Count / min']
        ]
        minutes = float(self.request['time_range'][1] - self.request['time_range'][0]) / 60.0
        minutes = max(minutes, 1.0)
        ports_in = []
        for row in ports:
            conn_row = []
            for h in headers:
                if h[0] == 'links':
                    conn_row.append(si_formatting(float(row['links']) / minutes))
                else:
                    conn_row.append(row[h[0]])
            ports_in.append(conn_row)
        response = {
            "page": page,
            "page_size": self.request['page_size'],
            "order": order,
            "component": "ports",
            "headers": headers,
            "rows": ports_in
        }
        return response

    def children(self, page, order):
        children = self.detailsModel.get_details_children(order)
        first = (page - 1) * self.page_size
        last = first + self.page_size

        response = {
            "page": page,
            "page_size": self.request['page_size'],
            "order": order,
            "count": len(children),
            "component": "children",
            "headers": [
                ['ipstart', "Address"],
                ['hostname', 'Name'],
                ['endpoints', 'Active Endpoints'],
                ['ratio', 'Role (0=client, 1=server)']
            ],
            "rows": children[first:last]
        }
        return response

    def summary(self):
        summary = self.detailsModel.get_details_summary()
        return summary

    def selection_info(self, page, order, simple):
        # called for selections in the map pane
        summary = self.summary()
        details = {'unique_out': summary.unique_out,
                   'unique_in': summary.unique_in,
                   'unique_ports': summary.unique_ports,
                   'inputs': self.inputs(page, order, simple),
                   'outputs': self.outputs(page, order, simple),
                   'ports': self.ports(page, order)}

        return details
