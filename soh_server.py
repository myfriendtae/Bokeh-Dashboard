from pandas import read_csv
from pandas import to_datetime

from os.path import dirname, join

from scipy import stats

from bokeh.layouts import row, layout
from bokeh.plotting import figure, curdoc, output_file, show
from bokeh.models import ColumnDataSource, HoverTool, Title, TextInput, Select, DataTable, DateFormatter, TableColumn, Div, Button, CustomJS


# Functions
def select_fill_color(row):
    # https://docs.bokeh.org/en/latest/docs/reference/colors.html?highlight=colors
    # fully allocated
    if row['system_qty'] <= row['reserved_qty']:
        return 'midnightblue'
    # nothing has been allocated
    elif row['reserved_qty'] == 0:
        return 'lightblue'
    # allocated but not fully
    else:
        return 'steelblue'

def select_line_color(row):
    if row['bdc'] == 'AVAIL':
        return 'green'
    elif row['bdc'] == 'QCLOCK':
        return 'yellow'
    else:
        return 'Red'

def make_status1(row):
    # fully allocated
    if row['system_qty'] <= row['reserved_qty']:
        return 'Fully allocated'
    # nothing has been allocated
    elif row['reserved_qty'] == 0:
        return 'Not allocated'
    # allocated but not fully
    else:
        return 'Partially allocated'

def make_status2(row):
    print('Warning: depreciation')
    if (row['bdc']=='AVAIL') or (row['bdc']=='QCPASSED'):
        return 'Available'
    elif (row['bdc']!='AVAIL') and (row['bdc']!='QCPASSED'):
        return 'No Available'
    else:
        return 'Unidentified'

# Load data
source_data = 'G:/Customer Documentation Team/Allocations Management/Database/physical_soh.csv'
df = read_csv(source_data)
df = df[~df['batch_loc'].isin(['lab', 'CCLMISSING', 'HMISSING', 'OMISSING', 'VMISSING', 'GMISSING', 'RMISSING', 'BMISSING', 'CHPMISSING', 'CDDMISSING'])]
df['item'] = df['item'].astype(int).astype(str)
df['fill_mapper'] = df.apply(lambda row: select_fill_color(row), axis=1)
df['line_mapper'] = df.apply(lambda row: select_line_color(row), axis=1)
df['status'] = df.apply(lambda row: make_status1(row), axis=1)
# df['status2'] = df.apply(lambda row: make_status2(row), axis=1)
# df['status'] = df[['status1', 'status2']].agg('-'.join, axis=1)

# Create a input controls
item_input = TextInput(placeholder="Item Number", value="")
bdc_input = Select(value='status', options=['All batches', 'Available batches', 'Not available batches'])
sum_text = Div(text="", width=500)

# Create Column data source that will be used by the plot
source = ColumnDataSource(data=dict(
    system_qty = [],
    system_size = [],
    man_date = [],
    reserved_qty = [],
    avail = [],
    batch = [],
    sales = [],
    bdc = [],
    status = [],
    fill_mapper = [],
    line_mapper = [],
))

hover = HoverTool(
    tooltips = [
        ("Manufacturing Date", "@man_date{%Y-%m-%d}"),
        ("Reserved Qty", "@reserved_qty"),
        ("System Qty", "@system_qty"),
        ("Available Qty", "@avail"),
        ("BDC", "@bdc"),
        ("Batch", "@batch"),
        ("Sales", "@sales"),
    ],
    formatters = {
        '@man_date': 'datetime'
    },
)

p = figure(x_axis_type='datetime', tools='box_select, reset') # pan, box_zoom, wheel_zoom, 


p.circle(
    x='man_date', y='system_qty',
    # size='system_size',
    size = 20, 
    alpha=0.7, line_width=2,
    fill_color = 'fill_mapper',
    line_color = 'line_mapper',
    hover_color='grey', hover_alpha=0.5,
    # legend_field='status',
    source=source,
)

date_format = DateFormatter(format='%Y-%m-%d')

columns = [
    TableColumn(field='batch', title='Batch'),
    TableColumn(field='system_qty', title='System Qty'),
    TableColumn(field='reserved_qty', title='Reserved Qty'),
    TableColumn(field='avail', title='Available Qty'),
    TableColumn(field='man_date', title='Manufacturing Date', formatter=date_format),
    TableColumn(field='bdc', title='BDC'),
    TableColumn(field='sales', title='Sales Number')
]
data_table = DataTable(source=source, columns=columns, index_position=None, width=900)


def select_data():
    bdc = bdc_input.value
    
    selected = df[df['item'] == str(item_input.value)].reset_index()

    if bdc == "Available batches":
        selected = selected[(selected['bdc']=='AVAIL')|(selected['bdc']=='QCPASSED')]
    elif bdc == 'Not available batches': 
        selected = selected[(selected['bdc']!='AVAIL')&(selected['bdc']!='QCPASSED')]
    
    return selected

def update():
    try:
        df1 = select_data()
        title = str(item_input.value) + ' ' + df1.iloc[0]['name']
        p.xaxis.axis_label = "Manufacturing Date"
        p.yaxis.axis_label = "Quantity"      
        p.title.text = title
        sum_text = Div(text="""<h3>Selected item(s):</h3> no item selected...""", width=500)

        source.data = dict(
            system_qty = df1['system_qty'],
            # system_size = stats.zscore(df1['system_qty'])*10+20,
            man_date = to_datetime(df1['man_date']),
            reserved_qty = df1['reserved_qty'],
            avail = df1['avail'],
            batch = df1['comb'],
            sales = df1['sales'],
            bdc = df1['bdc'],
            status = df1['status'],
            fill_mapper= df1['fill_mapper'],
            line_mapper = df1['line_mapper'],
        )
        p.add_tools(hover)
        update_text(df1)

    except IndexError:
        # print('Index error')
        title = item_input.value + " is not exist. Please check the item number."
        p.title.text = title
        source.data = dict(
            system_qty = [],
            # system_size = [],
            man_date = [],
            reserved_qty = [],
            avail = [],
            batch = [],
            sales = [],
            bdc = [],
            status = [],
            fill_mapper = [],
            line_mapper = [],
        )
    except:
        raise

def update_text(data):
    total_system_qty = sum(data['system_qty'])
    total_avail_qty = sum(data['avail'])
    total_reserved_qty = sum(data['reserved_qty'])
    sum_text.text = '<p><strong>*Selected item(s):</strong>' + '<br>Total system qty: &emsp;' + str(int(total_system_qty)) + '<br>Total available qty: &emsp;' + str(int(total_avail_qty)) + '<br>Total reserved qty: &emsp;' + str(int(total_reserved_qty)) + '</p>'
    
def selection_change(attr, old, new):
    selected = source.selected.indices
    data = select_data()
    if selected:
        data = data.iloc[selected, :]
    update_text(data)


# button model
button = Button(label="Download", button_type="success")
button.js_on_click(CustomJS(args=dict(source=source),
                            code=open(join(dirname(__file__), "download.js")).read()))

source.selected.on_change('indices', selection_change)

controls = [item_input, bdc_input]
for control in controls:
    control.on_change('value', lambda attr, old, new: update())

inputs = row(*controls)

l = layout([
    [inputs, button],
    [p, [data_table, sum_text]],
])

update() # initial load of the data

curdoc().add_root(l)
curdoc().title = "Allocations Report"




