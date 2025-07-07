"""
Moyasar payment gateway service for handling payments and webhooks.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from decimal import Decimal
import requests
import json
import hmac
import hashlib
from datetime import datetime
import uuid

from app.models.payment import Payment, PaymentGatewayLog, PaymentStatus, PaymentGateway
from app.models.cart import Cart
from app.models.student import Student
from app.core.config import settings


class MoyasarService:
    """
    Service for handling Moyasar payment gateway operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.MOYASAR_API_KEY
        self.webhook_secret = settings.MOYASAR_WEBHOOK_SECRET
        self.base_url = "https://api.moyasar.com/v1"
        self.headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str = "SAR",
        description: str = "Course purchase",
        customer_info: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent with Moyasar.
        """
        # Convert amount to halalas (smallest currency unit)
        amount_halalas = int(amount * 100)
        
        payment_data = {
            "amount": amount_halalas,
            "currency": currency,
            "description": description,
            "metadata": metadata or {}
        }
        
        # Add customer information if provided
        if customer_info:
            payment_data.update({
                "source": {
                    "type": "creditcard",
                    "name": customer_info.get("name", ""),
                    "number": customer_info.get("card_number", ""),
                    "cvc": customer_info.get("cvc", ""),
                    "month": customer_info.get("exp_month", ""),
                    "year": customer_info.get("exp_year", "")
                }
            })
        
        try:
            response = requests.post(
                f"{self.base_url}/payments",
                headers=self.headers,
                json=payment_data,
                timeout=30
            )
            
            response_data = response.json()
            
            # Log the request and response
            self._log_gateway_interaction(
                payment_id=None,
                request_data=payment_data,
                response_data=response_data,
                status=response_data.get("status", "unknown"),
                response_code=str(response.status_code)
            )
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "payment_id": response_data.get("id"),
                    "status": response_data.get("status"),
                    "amount": response_data.get("amount"),
                    "currency": response_data.get("currency"),
                    "source": response_data.get("source", {}),
                    "transaction_url": response_data.get("transaction_url"),
                    "data": response_data
                }
            else:
                return {
                    "success": False,
                    "error": response_data.get("message", "Payment creation failed"),
                    "error_code": response_data.get("type"),
                    "data": response_data
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "error_code": "network_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_code": "unexpected_error"
            }
    
    def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify payment status with Moyasar.
        """
        try:
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self.headers,
                timeout=30
            )
            
            response_data = response.json()
            
            # Log the verification request
            self._log_gateway_interaction(
                payment_id=payment_id,
                request_data={"action": "verify_payment"},
                response_data=response_data,
                status=response_data.get("status", "unknown"),
                response_code=str(response.status_code)
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "payment_id": response_data.get("id"),
                    "status": response_data.get("status"),
                    "amount": response_data.get("amount"),
                    "currency": response_data.get("currency"),
                    "paid_at": response_data.get("paid_at"),
                    "source": response_data.get("source", {}),
                    "metadata": response_data.get("metadata", {}),
                    "data": response_data
                }
            else:
                return {
                    "success": False,
                    "error": response_data.get("message", "Payment verification failed"),
                    "error_code": response_data.get("type"),
                    "data": response_data
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "error_code": "network_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_code": "unexpected_error"
            }
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "Refund requested"
    ) -> Dict[str, Any]:
        """
        Refund a payment through Moyasar.
        """
        refund_data = {
            "reason": reason
        }
        
        if amount:
            # Convert amount to halalas
            refund_data["amount"] = int(amount * 100)
        
        try:
            response = requests.post(
                f"{self.base_url}/payments/{payment_id}/refund",
                headers=self.headers,
                json=refund_data,
                timeout=30
            )
            
            response_data = response.json()
            
            # Log the refund request
            self._log_gateway_interaction(
                payment_id=payment_id,
                request_data=refund_data,
                response_data=response_data,
                status=response_data.get("status", "unknown"),
                response_code=str(response.status_code)
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "refund_id": response_data.get("id"),
                    "status": response_data.get("status"),
                    "amount": response_data.get("amount"),
                    "currency": response_data.get("currency"),
                    "refunded_at": response_data.get("refunded_at"),
                    "data": response_data
                }
            else:
                return {
                    "success": False,
                    "error": response_data.get("message", "Refund failed"),
                    "error_code": response_data.get("type"),
                    "data": response_data
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "error_code": "network_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_code": "unexpected_error"
            }
    
    def process_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Process Moyasar webhook payload.
        """
        # Verify webhook signature
        if not self._verify_webhook_signature(payload, signature):
            return {
                "success": False,
                "error": "Invalid webhook signature",
                "error_code": "invalid_signature"
            }
        
        try:
            # Parse webhook payload
            webhook_data = json.loads(payload.decode('utf-8'))
            
            event_type = webhook_data.get("type")
            payment_data = webhook_data.get("data", {})
            
            # Log webhook received
            self._log_gateway_interaction(
                payment_id=payment_data.get("id"),
                request_data={"webhook_type": event_type},
                response_data=webhook_data,
                status=event_type,
                response_code="200"
            )
            
            # Process different webhook events
            if event_type == "payment_paid":
                return self._handle_payment_paid(payment_data)
            elif event_type == "payment_failed":
                return self._handle_payment_failed(payment_data)
            elif event_type == "payment_refunded":
                return self._handle_payment_refunded(payment_data)
            else:
                return {
                    "success": True,
                    "message": f"Webhook event {event_type} received but not processed",
                    "event_type": event_type
                }
        
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON payload",
                "error_code": "invalid_json"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Webhook processing error: {str(e)}",
                "error_code": "processing_error"
            }
    
    def _verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature to ensure it's from Moyasar.
        """
        if not self.webhook_secret:
            return True  # Skip verification if no secret is configured
        
        try:
            # Create expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
        
        except Exception:
            return False
    
    def _handle_payment_paid(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment paid webhook event.
        """
        moyasar_payment_id = payment_data.get("id")
        
        # Find payment in database
        payment = self.db.query(Payment).filter(
            Payment.payment_id == moyasar_payment_id
        ).first()
        
        if not payment:
            return {
                "success": False,
                "error": "Payment not found in database",
                "error_code": "payment_not_found"
            }
        
        # Update payment status
        payment.payment_status = PaymentStatus.PAID
        payment.confirmed_at = datetime.utcnow()
        payment.gateway_response = payment_data
        
        # Update transaction ID if provided
        if payment_data.get("source", {}).get("transaction_id"):
            payment.transaction_id = payment_data["source"]["transaction_id"]
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Payment marked as paid",
            "payment_id": payment.id,
            "moyasar_payment_id": moyasar_payment_id
        }
    
    def _handle_payment_failed(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment failed webhook event.
        """
        moyasar_payment_id = payment_data.get("id")
        
        # Find payment in database
        payment = self.db.query(Payment).filter(
            Payment.payment_id == moyasar_payment_id
        ).first()
        
        if not payment:
            return {
                "success": False,
                "error": "Payment not found in database",
                "error_code": "payment_not_found"
            }
        
        # Update payment status
        payment.payment_status = PaymentStatus.FAILED
        payment.gateway_response = payment_data
        
        # Add failure reason if available
        if payment_data.get("source", {}).get("message"):
            payment.notes = payment_data["source"]["message"]
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Payment marked as failed",
            "payment_id": payment.id,
            "moyasar_payment_id": moyasar_payment_id
        }
    
    def _handle_payment_refunded(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment refunded webhook event.
        """
        moyasar_payment_id = payment_data.get("id")
        
        # Find payment in database
        payment = self.db.query(Payment).filter(
            Payment.payment_id == moyasar_payment_id
        ).first()
        
        if not payment:
            return {
                "success": False,
                "error": "Payment not found in database",
                "error_code": "payment_not_found"
            }
        
        # Update payment status
        payment.payment_status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.utcnow()
        payment.gateway_response = payment_data
        
        # Update refunded amount
        if payment_data.get("amount"):
            payment.refunded_amount = Decimal(payment_data["amount"]) / 100
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Payment marked as refunded",
            "payment_id": payment.id,
            "moyasar_payment_id": moyasar_payment_id
        }
    
    def _log_gateway_interaction(
        self,
        payment_id: Optional[str],
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        status: str,
        response_code: str
    ):
        """
        Log gateway interaction for debugging and audit purposes.
        """
        # Find payment record if payment_id exists
        payment_record = None
        if payment_id:
            payment_record = self.db.query(Payment).filter(
                Payment.payment_id == payment_id
            ).first()
        
        log_entry = PaymentGatewayLog(
            payment_id=payment_record.id if payment_record else None,
            gateway="moyasar",
            gateway_transaction_id=payment_id,
            request_data=request_data,
            response_data=response_data,
            status=status,
            response_code=response_code,
            response_message=response_data.get("message", "")
        )
        
        self.db.add(log_entry)
        self.db.commit()
    
    def get_payment_methods(self) -> List[Dict[str, Any]]:
        """
        Get available payment methods for Moyasar.
        """
        return [
            {
                "id": "creditcard",
                "name": "Credit Card",
                "type": "card",
                "supported_cards": ["visa", "mastercard", "amex"],
                "currency": "SAR",
                "min_amount": 1.00,
                "max_amount": 10000.00,
                "fees": {
                    "percentage": 2.9,
                    "fixed": 0.00
                }
            },
            {
                "id": "stcpay",
                "name": "STC Pay",
                "type": "wallet",
                "currency": "SAR",
                "min_amount": 1.00,
                "max_amount": 5000.00,
                "fees": {
                    "percentage": 2.0,
                    "fixed": 0.00
                }
            },
            {
                "id": "applepay",
                "name": "Apple Pay",
                "type": "wallet",
                "currency": "SAR",
                "min_amount": 1.00,
                "max_amount": 10000.00,
                "fees": {
                    "percentage": 2.9,
                    "fixed": 0.00
                }
            }
        ] 