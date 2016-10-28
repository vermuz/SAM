import common
import web
import filters
import dbaccess


class Table(object):
    def __init__(self):
        self.pageTitle = "Host List"
        # self.columns = ["Address", "Hostname", "Role", "Environment", "Tags"]
        self.columns = ["Address", "Alias", "Connections in", "Connections out"]

    def GET(self):
        print("="*50)
        fs = None
        get_data = web.input()
        if "filters" in get_data:
            print "filters: ", get_data["filters"], "\n"
            fs = filters.readEncoded(get_data["filters"])
            for i in fs:
                print i.testString()
        print("="*50)

        page = 1
        if 'page' in get_data:
            page = int(get_data['page'])
        page_size = 10
        if 'page_size' in get_data:
            page_size = int(get_data['page_size'])

        rows = []
        if fs:
            # The page-1 is because page 1 should start with result 0;
            # The page_size+1 is so that IF it gets filled I know there's at least 1 more page to display.
            data = dbaccess.get_table_info(fs, page - 1, page_size + 1)
            rows = []
            for i in range(len(data)):
                row = [data[i].address]
                if data[i].alias:
                    row.append(data[i].alias)
                else:
                    row.append("-")

                if data[i].conn_in:
                    row.append(data[i].conn_in)
                else:
                    row.append(0)

                if data[i].conn_out:
                    row.append(data[i].conn_out)
                else:
                    row.append(0)

                rows.append(row)

        if rows:
            spread = "results {0} to {1}".format((page-1)*page_size, (page-1)*page_size + len(rows[:10]))
            if len(rows) > page_size:
                spread += " -> "
            if page > 1:
                spread = " <- " + spread
        else:
            spread = "No matching results."


        if len(rows) > page_size:
            path = web.ctx.fullpath
            page_i = path.find("page=")
            if page_i != -1:
                ampPos = path.find('&', page_i)
                nextPage = "{0}page={1}{2}".format(path[:page_i], page + 1, path[ampPos:])
            else:
                nextPage = path + "&page={0}".format(page + 1)
        else:
            nextPage = False
        if page > 1:
            path = web.ctx.fullpath
            page_i = path.find("page=")
            if page_i != -1:
                ampPos = path.find('&', page_i)
                prevPage = "{0}page={1}{2}".format(path[:page_i], page - 1, path[ampPos:])
            else:
                prevPage = path + "&page={0}".format(page - 1)
        else:
            prevPage = False

        return str(common.render._head(self.pageTitle,
                                       stylesheets=["/static/css/table.css"],
                                       scripts=["/static/js/table.js",
                                                "/static/js/table_filters.js"])) \
               + str(common.render._header(common.navbar, self.pageTitle)) \
               + str(common.render.table(self.columns, rows[:10], spread, prevPage, nextPage)) \
               + str(common.render._tail())
