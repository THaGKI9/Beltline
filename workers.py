
def jinja2(beltline, src_ext='.html'):
    from jinja2 import DictLoader, Environment

    template_dict = {
        product.path: product.data.decode('utf-8')
        for product in beltline.products
        if product.ext == src_ext
    }

    loader = DictLoader(template_dict)
    env = Environment(loader=loader)

    for product in beltline.products:
        if product.ext == src_ext:
            template = env.get_template(product.path)
            product.data = template.render().encode('utf-8')
