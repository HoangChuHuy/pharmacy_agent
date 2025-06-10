from pydantic import BaseModel, Field


class MedicineDetail(BaseModel):
    name: str = Field("", description="Tên thuốc, là khóa chính và khóa ngoại liên kết với bảng products.")
    type: str = Field("", description="Loại danh mục thuốc đó")
    specification: str = Field("", description="Cách đóng gói thuốc có thể là túp vỉ viên nén")
    assign: str = Field("", description="Chỉ định dành cho những trường hợp nào")
    short_description: str = Field("", description="Mô tả ngắn về loại thuốc")
    ingredient: str = Field("", description="Thành phần hoạt chất chính của thuốc.")
    usage: str = Field("", description="Công dụng hoặc chỉ định của thuốc.'")
    dosage: str = Field("", description="Liều dùng được khuyến nghị.")
    adverseEffect: str = Field("", description="Tác dụng phụ có thể xảy ra khi dùng thuốc")
    careful: str = Field("", description="Các lưu ý và thận trọng khi sử dụng thuốc.")
    preservation: str = Field("", description="Cách bảo quản thuốc.")
    price: str = Field("", description="Giá bán của thuốc.")
    image_url: str = Field("", description="URL hình ảnh minh họa cho thuốc.")
    note: str = Field("", description="Lưu ý khi sử dụng thuốc")
    FAQ: str = Field("", description="Các câu hỏi thường gặp")
    rate: str = Field("", description="Đánh giá về sản phẩm")
    QA: str = Field("", description="Các bình luận về sản phẩm")



