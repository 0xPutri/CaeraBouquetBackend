from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    """Menyajikan data kategori secara ringkas untuk katalog.

    Serializer ini digunakan saat frontend membutuhkan identitas dasar
    kategori tanpa memuat informasi tambahan yang tidak diperlukan.
    """

    class Meta:
        model = Category
        fields = ('id', 'name')

class ProductSerializer(serializers.ModelSerializer):
    """Menyajikan data produk untuk kebutuhan katalog publik.

    Serializer ini menampilkan informasi inti produk yang relevan bagi
    pelanggan saat melihat daftar maupun detail produk.
    """

    category = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'external_product_id', 'name', 'price', 'category', 'description', 'image_url')
