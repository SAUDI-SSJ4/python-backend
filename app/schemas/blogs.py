from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class BlogPostBase(BaseModel):
    """Base schema for blog posts."""
    title: str = Field(..., min_length=3, max_length=255, description="Post title")
    content: str = Field(..., description="Post content")
    summary: Optional[str] = Field(None, max_length=500, description="Post summary")
    featured_image: Optional[str] = Field(None, description="URL to featured image")
    is_featured: bool = Field(False, description="Whether the post is featured")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Introduction to FastAPI",
                "content": "FastAPI is a modern API framework...",
                "summary": "A brief overview of FastAPI features",
                "featured_image": "/static/uploads/fastapi-intro.jpg",
                "is_featured": False
            }
        }


class BlogPostCreate(BlogPostBase):
    """Schema for creating a new blog post."""
    tags: Optional[List[str]] = Field(default=[], description="List of tags")
    excerpt: Optional[str] = Field(None, max_length=500, description="Post excerpt")
    slug: Optional[str] = Field(None, description="URL slug")
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    meta_keywords: Optional[List[str]] = Field(default=[], description="SEO keywords")
    status: str = Field("draft", description="Post status")
    category_id: Optional[int] = Field(None, description="Category ID")


class BlogPostUpdate(BaseModel):
    """Schema for updating an existing blog post."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None)
    excerpt: Optional[str] = Field(None, max_length=500)
    featured_image: Optional[str] = Field(None)
    is_featured: Optional[bool] = Field(None)
    tags: Optional[List[str]] = Field(None)
    meta_description: Optional[str] = Field(None)
    meta_keywords: Optional[List[str]] = Field(None)
    status: Optional[str] = Field(None)
    category_id: Optional[int] = Field(None)
    slug: Optional[str] = Field(None)


class AuthorBase(BaseModel):
    """Base schema for blog author."""
    id: int
    name: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None


class CategoryBase(BaseModel):
    """Base schema for blog category."""
    id: int
    name: str
    slug: str
    description: Optional[str] = None


class BlogPost(BlogPostBase):
    """Schema for detailed blog post."""
    id: int
    slug: str
    excerpt: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[List[str]] = []
    author: AuthorBase
    category: CategoryBase
    tags: List[str] = []
    status: str
    views_count: int = 0
    comments_count: int = 0
    likes_count: int = 0
    shares_count: int = 0
    reading_time: int = 0
    seo_score: Optional[int] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    related_posts: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        from_attributes = True


class BlogPostPublic(BaseModel):
    """Schema for public blog post listing."""
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    author: Dict[str, Any]
    category: Dict[str, Any]
    tags: List[str] = []
    status: str = "published"
    views_count: int = 0
    comments_count: Optional[int] = None
    reading_time: Optional[int] = None
    is_featured: bool = False
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BlogPostInDB(BlogPostBase):
    """Schema for blog post as stored in DB."""
    id: int
    slug: str
    author_id: int
    category_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BlogPostList(BaseModel):
    """Schema for list of blog posts."""
    total: int
    posts: List[BlogPostPublic]
    
    class Config:
        from_attributes = True


# Tags schemas
class TagBase(BaseModel):
    """Base schema for tags."""
    name: str = Field(..., min_length=2, max_length=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "FastAPI"
            }
        }


class TagCreate(TagBase):
    """Schema for creating a new tag."""
    pass


class TagInDB(TagBase):
    """Schema for tag as stored in DB."""
    id: int
    
    class Config:
        from_attributes = True


class TagResponse(TagInDB):
    """Schema for tag response."""
    post_count: int = 0
    
    class Config:
        from_attributes = True 