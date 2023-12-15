
// A collection of format functions for objects returned by the /dataset/attributes
let fmt = {
    id: x=>x ? x.id : '',
    name: x=>x ? x.name : '',
    site: x => x ? '#' + x.id + ' (' + x.name + ')' : '#???',
    user: x=>x.firstname + ' ' + x.surname,
    self: x => x
}

class SiteFilter {
    constructor(project, valuetype, user, max_data_age, instrument, date, fulltext) {
        this.project = project || $('#prjselect').val()
        this.valuetype = valuetype || $('#vtselect').val()
        this.user =  user || $('#userselect').val()
        this.max_data_age = max_data_age || $('#max_data_age').val()
        this.instrument =  instrument || $('#instrumentselect').val()
        this.date =  date || $('#dateselect').val()
        this.fulltext =  fulltext || $('#fulltext').val()
    }

    populate_form() {
        let options = (data, get_value, get_name) => {
            let html = '<option class="firstoption" value="">Please select...</option>\n';
            $.each(data, (index, item) => {
                html += '<option value="' + get_value(item) + '">' + get_name(item) + '</option>\n';
            });
            return html

        }

        $('#datasetsonly').prop('checked',(this.project || this.valuetype || this.user || this.date || this.max_data_age));

        $.getJSON(
            odmf_ref('/dataset/attributes'),
            {
                project: this.project,
                valuetype: this.valuetype,
                user:this.user,
                date:this.date,
            },
            data => {
                $('#vtselect').html(options(data.valuetype, fmt.id, fmt.name)).val(this.valuetype);
                $('#userselect').html(options(data.measured_by, x=>x.username, fmt.user)).val(this.user)
                $('#prjselect').html(options(data.project, fmt.id, fmt.name)).val(this.project)
            }
        );
        $.get(odmf_ref('/site/getinstalledinstruments'), {}, function(data){
            data.unshift({id: 'any', name: 'any'})
            data.unshift({id: 'installed', name: 'any installed instrument'})
            let html = options(data, fmt.id, fmt.name)
            $('#instrumentselect').html(html).val(filter.instrument);
        }).fail(jqhxr => seterror(jqhxr.responseText));

        return this
    }

    apply(callback, source) {
        source = source || odmf_ref('/site/json')
        $.getJSON(source, this, callback)
    }
}

function clearFilter() {
    $('.filter').val('');
    $('#dateselect').val('');
    $('#datasetsonly').prop('checked',false);
    let sf=new SiteFilter()
    sf.populate_form()

}
$(()=>{
    $('#clear-filter').on('click', () => {
        clearFilter()
        $('.filter').first().trigger('change')
    })
    $('#apply-filter').on('click', ()=>{
        $('.filter').first().trigger('change')
    })
})