from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_student, get_optional_current_user

router = APIRouter()


# Mock data generators
def generate_mock_blog(blog_id: int, academy_id: int):
    return {
        "id": blog_id,
        "academy_id": academy_id,
        "title": f"Academy {academy_id} Blog",
        "description": "Stay updated with our latest news and articles",
        "is_active": True,
        "meta_title": f"Academy {academy_id} Blog - Educational Articles",
        "meta_description": "Read our latest educational articles and insights",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


def generate_mock_blog_category(category_id: int):
    categories = ["Technology", "Education", "Science", "Business", "Health"]
    return {
        "id": category_id,
        "name": categories[(category_id - 1) % len(categories)],
        "slug": categories[(category_id - 1) % len(categories)].lower(),
        "description": f"Articles about {categories[(category_id - 1) % len(categories)]}",
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }


def generate_mock_blog_post(post_id: int, blog_id: int, academy_id: int):
    return {
        "id": post_id,
        "blog_id": blog_id,
        "academy_id": academy_id,
        "category_id": (post_id % 5) + 1,
        "title": f"Post {post_id}: The Future of Online Education",
        "slug": f"post-{post_id}-future-online-education",
        "content": """
        <h2>Introduction</h2>
        <p>Online education has revolutionized the way we learn...</p>
        <h2>Key Benefits</h2>
        <ul>
            <li>Flexibility in learning</li>
            <li>Access to global expertise</li>
            <li>Cost-effective solutions</li>
        </ul>
        <h2>Conclusion</h2>
        <p>The future of education is digital...</p>
        """,
        "excerpt": "Discover how online education is transforming learning worldwide",
        "featured_image": f"https://example.com/blog{post_id}.jpg",
        "author_name": f"Author {(post_id % 3) + 1}",
        "is_published": True,
        "is_featured": post_id % 4 == 0,
        "views_count": 500 + (post_id * 50),
        "likes_count": 50 + (post_id * 5),
        "meta_title": f"Post {post_id}: Online Education Future",
        "meta_description": "Learn about the future of online education",
        "published_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


def generate_mock_comment(comment_id: int, post_id: int, student_id: Optional[int] = None):
    return {
        "id": comment_id,
        "post_id": post_id,
        "student_id": student_id,
        "name": f"User {comment_id}" if not student_id else None,
        "email": f"user{comment_id}@example.com" if not student_id else None,
        "content": f"Great article! Very informative. Comment #{comment_id}",
        "is_approved": True,
        "created_at": datetime.now().isoformat()
    }


# Blog endpoints
@router.get("/")
def get_blogs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    academy_id: Optional[int] = None,
    is_active: bool = True
) -> Any:
    """Get list of active blogs"""
    blogs = [generate_mock_blog(i, i) for i in range(1, 11)]
    
    if academy_id:
        blogs = [b for b in blogs if b["academy_id"] == academy_id]
    if is_active:
        blogs = [b for b in blogs if b["is_active"]]
    
    return {
        "data": blogs[skip:skip + limit],
        "total": len(blogs),
        "skip": skip,
        "limit": limit
    }


@router.get("/{blog_id}")
def get_blog(blog_id: int) -> Any:
    """Get blog details"""
    return generate_mock_blog(blog_id, 1)


# Blog posts endpoints
@router.get("/posts")
def get_blog_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    academy_id: Optional[int] = None,
    category_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    is_published: bool = True
) -> Any:
    """Get list of blog posts"""
    posts = [generate_mock_blog_post(i, 1, 1) for i in range(1, 21)]
    
    if academy_id:
        posts = [p for p in posts if p["academy_id"] == academy_id]
    if category_id:
        posts = [p for p in posts if p["category_id"] == category_id]
    if is_featured is not None:
        posts = [p for p in posts if p["is_featured"] == is_featured]
    if is_published:
        posts = [p for p in posts if p["is_published"]]
    
    return {
        "data": posts[skip:skip + limit],
        "total": len(posts),
        "skip": skip,
        "limit": limit
    }


@router.get("/posts/{post_id}")
def get_blog_post(
    post_id: int,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Get blog post details"""
    post = generate_mock_blog_post(post_id, 1, 1)
    
    # Increment view count
    post["views_count"] += 1
    
    # Add category details
    post["category"] = generate_mock_blog_category(post["category_id"])
    
    # Add related posts
    post["related_posts"] = [
        generate_mock_blog_post(i, 1, 1) for i in range(post_id + 1, post_id + 4)
    ]
    
    return post


# Categories endpoints
@router.get("/categories")
def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: bool = True
) -> Any:
    """Get list of blog categories"""
    categories = [generate_mock_blog_category(i) for i in range(1, 6)]
    
    if is_active:
        categories = [c for c in categories if c["is_active"]]
    
    return {
        "data": categories[skip:skip + limit],
        "total": len(categories),
        "skip": skip,
        "limit": limit
    }


@router.get("/categories/{category_id}/posts")
def get_category_posts(
    category_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> Any:
    """Get posts by category"""
    posts = [generate_mock_blog_post(i, 1, 1) for i in range(1, 21)]
    posts = [p for p in posts if p["category_id"] == category_id]
    
    return {
        "data": posts[skip:skip + limit],
        "total": len(posts),
        "skip": skip,
        "limit": limit,
        "category": generate_mock_blog_category(category_id)
    }


# Comments endpoints
@router.get("/posts/{post_id}/comments")
def get_post_comments(
    post_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_approved: bool = True
) -> Any:
    """Get comments for a blog post"""
    comments = [generate_mock_comment(i, post_id, i % 3 if i % 2 == 0 else None) for i in range(1, 16)]
    
    if is_approved:
        comments = [c for c in comments if c["is_approved"]]
    
    return {
        "data": comments[skip:skip + limit],
        "total": len(comments),
        "skip": skip,
        "limit": limit
    }


@router.post("/posts/{post_id}/comments")
def create_comment(
    post_id: int,
    comment_data: dict,
    current_user = Depends(get_optional_current_user)
) -> Any:
    """Create a new comment on a blog post"""
    comment_id = 101
    student_id = current_user.id if current_user else None
    
    return {
        "id": comment_id,
        "post_id": post_id,
        "student_id": student_id,
        "name": comment_data.get("name") if not student_id else None,
        "email": comment_data.get("email") if not student_id else None,
        "content": comment_data.get("content", ""),
        "is_approved": False,  # Needs approval
        "created_at": datetime.now().isoformat()
    }


@router.put("/comments/{comment_id}")
def update_comment(
    comment_id: int,
    comment_data: dict,
    current_user = Depends(get_current_student)
) -> Any:
    """Update own comment"""
    return {
        "id": comment_id,
        "content": comment_data.get("content", "Updated comment"),
        "updated_at": datetime.now().isoformat(),
        "message": "Comment updated successfully"
    }


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user = Depends(get_current_student)
) -> Any:
    """Delete own comment"""
    return {"message": f"Comment {comment_id} deleted successfully"}


# Search endpoint
@router.get("/search")
def search_posts(
    q: str = Query(..., min_length=3),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> Any:
    """Search blog posts"""
    # Mock search results
    posts = [generate_mock_blog_post(i, 1, 1) for i in range(1, 6)]
    
    # Simulate search by modifying titles
    for post in posts:
        post["title"] = f"{post['title']} - '{q}'"
        post["excerpt"] = f"Search results for '{q}': {post['excerpt']}"
    
    return {
        "data": posts[skip:skip + limit],
        "total": len(posts),
        "query": q,
        "skip": skip,
        "limit": limit
    } 