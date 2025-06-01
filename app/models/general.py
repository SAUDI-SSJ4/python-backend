from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# Association table for many-to-many relationship between blog posts and keywords
blog_post_keywords = Table(
    'blog_post_keywords',
    Base.metadata,
    Column('blog_post_id', Integer, ForeignKey('blog_posts.id'), primary_key=True),
    Column('blog_keyword_id', Integer, ForeignKey('blog_keywords.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


class Blog(Base):
    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True, index=True)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    academy = relationship("Academy", back_populates="blogs")
    posts = relationship("BlogPost", back_populates="blog")


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    posts = relationship("BlogPost", back_populates="category")


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    blog_id = Column(Integer, ForeignKey("blogs.id"), nullable=False)
    academy_id = Column(Integer, ForeignKey("academies.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("blog_categories.id"), nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text, nullable=True)
    featured_image = Column(String(255), nullable=True)
    author_name = Column(String(255), nullable=True)
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    blog = relationship("Blog", back_populates="posts")
    academy = relationship("Academy", back_populates="blog_posts")
    category = relationship("BlogCategory", back_populates="posts")
    comments = relationship("BlogComment", back_populates="post")
    keywords = relationship("BlogKeyword", secondary=blog_post_keywords, back_populates="posts")


class BlogComment(Base):
    __tablename__ = "blog_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    post = relationship("BlogPost", back_populates="comments")
    student = relationship("Student", back_populates="blog_comments")


class BlogKeyword(Base):
    __tablename__ = "blog_keywords"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    posts = relationship("BlogPost", secondary=blog_post_keywords, back_populates="keywords")


class BlogPostKeyword(Base):
    __tablename__ = "blog_post_keyword"
    
    blog_post_id = Column(Integer, ForeignKey("blog_posts.id"), primary_key=True)
    blog_keyword_id = Column(Integer, ForeignKey("blog_keywords.id"), primary_key=True) 