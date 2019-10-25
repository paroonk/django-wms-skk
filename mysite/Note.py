class ProductDatabaseView(generic.ListView):
    template_name = 'wms/product_db.html'
    context_object_name = 'product_db'
    model = Product
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(ProductDatabaseView, self).get_context_data(**kwargs)
        qty_storage = {}
        for product in Product.objects.all():
            column_list = Column.objects.filter(usage='S', storage_product=product.product_id).values_list('column_id', flat=True)
            storage_count = Storage.objects.filter(column_id__in=column_list).count()
            qty_per_pallet = Product.objects.get(product_id=product.product_id).qty_limit
            qty_storage[product.product_id] = storage_count * qty_per_pallet
        context['qty_storage'] = qty_storage
        return context




<div class="table-responsive-lg">
    {% if is_paginated %}
    <ul class="pagination justify-content-center flex-wrap">
        {% if page_obj.has_previous %}
        <li class="page-item"><a class="page-link" href="?page=1">First</a></li>
        <li class="page-item"><a class="page-link" href="?page={{ page_obj.previous_page_number }}">&laquo;</a></li>
        {% else %}
        <li class="page-item disabled"><a class="page-link" href="?page=1">First</a></li>
        <li class="page-item disabled"><span class="page-link">&laquo;</span></li>
        {% endif %}
        {% for i in paginator.page_range %}
        {% if page_obj.number == i %}
        <li class="page-item active"><span class="page-link">{{ i }} <span class="sr-only">(current)</span></span></li>
        {% else %}
        <li class="page-item"><a class="page-link" href="?page={{ i }}">{{ i }}</a></li>
        {% endif %}
        {% endfor %}
        {% if page_obj.has_next %}
        <li class="page-item"><a class="page-link" href="?page={{ page_obj.next_page_number }}">&raquo;</a></li>
        <li class="page-item"><a class="page-link" href="?page={{ paginator.num_pages }}">Last</a></li>
        {% else %}
        <li class="page-item disabled"><span class="page-link">&raquo;</span></li>
        <li class="page-item disabled"><a class="page-link" href="?page={{ paginator.num_pages }}">Last</a></li>
        {% endif %}
    </ul>
    {% endif %}
    <table class="table table-sm table-hover">
        <thead class="thead">
        <tr>
            <th>Plant</th>
            <th>Product ID</th>
            <th>Name TH</th>
            <th>Name EN</th>
            <th>Max Quantity Per Pallet</th>
            <th>Total Space In Storage</th>
        </tr>
        </thead>
        <tbody id="table_db">
        {% for product in product_db %}
        <tr>
            <td>{{ product.plant }}</td>
            <td>{{ product.product_id }}</td>
            <td>{{ product.name_th }}</td>
            <td>{{ product.name_en }}</td>
            <td>{{ product.qty_limit }}</td>
            <td>{{ product.qty_storage }}</td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</div>


<img src="http://placekitten.com/50/50" width="400" height="400" style="position: absolute; z-index: -1; opacity: 0.5;">