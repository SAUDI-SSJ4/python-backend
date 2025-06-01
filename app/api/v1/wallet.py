from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import random

from app.deps import get_db, get_current_academy_user

router = APIRouter()


def generate_mock_wallet():
    """Generate mock wallet data"""
    return {
        "balance": round(random.uniform(1000, 50000), 2),
        "total_earned": round(random.uniform(10000, 100000), 2),
        "total_withdrawn": round(random.uniform(5000, 30000), 2),
        "pending_withdrawals": round(random.uniform(0, 5000), 2),
        "currency": "SAR",
        "updated_at": datetime.now().isoformat()
    }


def generate_mock_transaction(trans_id: int, academy_id: int):
    """Generate mock transaction"""
    trans_types = ["payment", "withdrawal", "commission", "refund"]
    trans_type = trans_types[trans_id % len(trans_types)]
    
    return {
        "id": f"TRX_{trans_id}_{academy_id}",
        "academy_id": academy_id,
        "type": trans_type,
        "amount": round(random.uniform(50, 1000), 2),
        "balance_before": round(random.uniform(1000, 10000), 2),
        "balance_after": round(random.uniform(1000, 10000), 2),
        "description": f"{trans_type.capitalize()} transaction #{trans_id}",
        "reference_id": f"REF_{trans_id}",
        "status": "completed",
        "created_at": (datetime.now() - timedelta(days=trans_id)).isoformat()
    }


def generate_mock_withdrawal(withdrawal_id: int, academy_id: int):
    """Generate mock withdrawal request"""
    statuses = ["pending", "approved", "rejected", "completed"]
    status = statuses[withdrawal_id % len(statuses)]
    
    return {
        "id": f"WD_{withdrawal_id}_{academy_id}",
        "academy_id": academy_id,
        "amount": round(random.uniform(500, 5000), 2),
        "status": status,
        "bank_name": "Al Rajhi Bank",
        "account_name": f"Academy {academy_id}",
        "account_number": f"****{random.randint(1000, 9999)}",
        "iban": f"SA{random.randint(10, 99)}XXXXXXXXXXXX{random.randint(1000, 9999)}",
        "notes": f"Withdrawal request #{withdrawal_id}",
        "admin_notes": "Processed successfully" if status == "completed" else None,
        "requested_at": (datetime.now() - timedelta(days=withdrawal_id * 2)).isoformat(),
        "approved_at": (datetime.now() - timedelta(days=withdrawal_id)).isoformat() if status in ["approved", "completed"] else None,
        "completed_at": datetime.now().isoformat() if status == "completed" else None
    }


# Wallet endpoints
@router.get("/")
def get_wallet(
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get academy wallet information"""
    wallet = generate_mock_wallet()
    wallet["academy_id"] = 1  # Mock academy ID
    
    # Add statistics
    wallet["statistics"] = {
        "today_earnings": round(random.uniform(100, 500), 2),
        "week_earnings": round(random.uniform(1000, 3000), 2),
        "month_earnings": round(random.uniform(5000, 15000), 2),
        "pending_payments": random.randint(5, 20),
        "total_students": random.randint(100, 500),
        "active_courses": random.randint(10, 30)
    }
    
    return wallet


@router.post("/withdraw")
def request_withdrawal(
    withdrawal_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Request withdrawal from wallet"""
    wallet = generate_mock_wallet()
    
    amount = withdrawal_data.get("amount", 0)
    
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid withdrawal amount"
        )
    
    if amount > wallet["balance"]:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )
    
    # Create withdrawal request
    withdrawal = {
        "id": f"WD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "academy_id": 1,
        "amount": amount,
        "status": "pending",
        "bank_name": withdrawal_data.get("bank_name"),
        "account_name": withdrawal_data.get("account_name"),
        "account_number": withdrawal_data.get("account_number"),
        "iban": withdrawal_data.get("iban"),
        "notes": withdrawal_data.get("notes"),
        "requested_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Withdrawal request submitted successfully",
        "withdrawal": withdrawal,
        "new_balance": wallet["balance"] - amount
    }


@router.get("/withdrawals")
def get_withdrawals(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get withdrawal history"""
    withdrawals = [generate_mock_withdrawal(i, 1) for i in range(1, 21)]
    
    # Filter by status
    if status:
        withdrawals = [w for w in withdrawals if w["status"] == status]
    
    return {
        "data": withdrawals[skip:skip + limit],
        "total": len(withdrawals),
        "skip": skip,
        "limit": limit
    }


@router.get("/stats")
def get_wallet_statistics(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get wallet statistics"""
    # Generate mock statistics based on period
    stats = {
        "period": period,
        "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "total_revenue": round(random.uniform(10000, 50000), 2),
        "total_withdrawals": round(random.uniform(5000, 20000), 2),
        "net_earnings": round(random.uniform(5000, 30000), 2),
        "commission_rate": 15,  # 15%
        "commission_paid": round(random.uniform(1500, 7500), 2),
        "transactions_count": random.randint(50, 200),
        "average_transaction": round(random.uniform(100, 300), 2),
        "growth_rate": round(random.uniform(-10, 30), 2),  # Percentage
        "chart_data": {
            "labels": [f"Day {i}" for i in range(1, 8)],
            "revenue": [round(random.uniform(500, 2000), 2) for _ in range(7)],
            "withdrawals": [round(random.uniform(0, 1000), 2) for _ in range(7)]
        }
    }
    
    return stats


@router.get("/transactions")
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get transaction history"""
    transactions = [generate_mock_transaction(i, 1) for i in range(1, 51)]
    
    # Filter by type
    if type:
        transactions = [t for t in transactions if t["type"] == type]
    
    # Sort by date (newest first)
    transactions.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "data": transactions[skip:skip + limit],
        "total": len(transactions),
        "skip": skip,
        "limit": limit
    }


@router.get("/completed-payments")
def get_completed_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get completed payments for academy courses"""
    payments = []
    
    for i in range(1, 31):
        payment = {
            "id": f"PAY_{i}",
            "student": {
                "id": i,
                "name": f"Student {i}",
                "email": f"student{i}@example.com"
            },
            "course": {
                "id": (i % 5) + 1,
                "title": f"Course {(i % 5) + 1}: Programming Basics",
                "price": 299.99
            },
            "amount": 299.99,
            "commission_rate": 15,
            "commission_amount": 45.00,
            "net_amount": 254.99,
            "payment_method": random.choice(["credit_card", "bank_transfer", "moyasar"]),
            "status": "completed",
            "paid_at": (datetime.now() - timedelta(days=i)).isoformat()
        }
        payments.append(payment)
    
    # Calculate summary
    summary = {
        "total_payments": len(payments),
        "total_amount": sum(p["amount"] for p in payments),
        "total_commission": sum(p["commission_amount"] for p in payments),
        "total_net": sum(p["net_amount"] for p in payments)
    }
    
    return {
        "data": payments[skip:skip + limit],
        "total": len(payments),
        "summary": summary,
        "skip": skip,
        "limit": limit
    }


# Bank account management
@router.get("/bank-accounts")
def get_bank_accounts(
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Get academy bank accounts"""
    accounts = [
        {
            "id": 1,
            "bank_name": "Al Rajhi Bank",
            "account_name": "Tech Academy Ltd",
            "account_number": "1234567890",
            "iban": "SA1234567890123456789012",
            "swift_code": "RJHISARI",
            "is_primary": True,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "bank_name": "NCB Bank",
            "account_name": "Tech Academy Ltd",
            "account_number": "0987654321",
            "iban": "SA0987654321098765432109",
            "swift_code": "NCBKSAJE",
            "is_primary": False,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
    ]
    
    return {"data": accounts}


@router.post("/bank-accounts")
def add_bank_account(
    account_data: dict,
    current_user = Depends(get_current_academy_user)
) -> Any:
    """Add new bank account"""
    account = {
        "id": 3,
        "bank_name": account_data.get("bank_name"),
        "account_name": account_data.get("account_name"),
        "account_number": account_data.get("account_number"),
        "iban": account_data.get("iban"),
        "swift_code": account_data.get("swift_code"),
        "is_primary": account_data.get("is_primary", False),
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Bank account added successfully",
        "account": account
    } 