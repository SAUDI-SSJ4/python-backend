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
import base64

from app.models.payment import Payment, PaymentGatewayLog, PaymentStatus, PaymentGateway
from app.models.cart import Cart
from app.models.student import Student
from app.core.config import settings


class MoyasarService:
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.MOYASAR_API_KEY
        self.webhook_secret = settings.MOYASAR_WEBHOOK_SECRET
        self.base_url = "https://api.moyasar.com/v1"
        self.timeout = 30
        
        if not self.api_key:
            raise ValueError("MOYASAR_API_KEY is not configured")
    
    def create_invoice(
        self,
        amount: int,
        currency: str = "SAR",
        description: str = "Payment",
        success_url: Optional[str] = None,
        back_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": amount,
                "currency": currency,
                "description": description,
                "publishable_api_key": self.api_key,
                "callback_url": callback_url,
                "success_url": success_url,
                "back_url": back_url,
                "metadata": metadata or {}
            }
            
            response = requests.post(
                f"{self.base_url}/invoices",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            log_entry = PaymentGatewayLog(
                gateway=PaymentGateway.MOYASAR,
                operation="create_invoice",
                request_data=json.dumps(payload),
                response_data=response.text,
                http_status=response.status_code,
                success=response.status_code == 201
            )
            self.db.add(log_entry)
            self.db.commit()
            
            if response.status_code == 201:
                invoice_data = response.json()
                return {
                    "success": True,
                    "invoice_id": invoice_data["id"],
                    "status": invoice_data["status"],
                    "payment_url": invoice_data.get("url"),
                    "amount": invoice_data["amount"],
                    "currency": invoice_data["currency"],
                    "expires_at": invoice_data.get("expires_at"),
                    "data": invoice_data
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("message", "فشل في إنشاء الفاتورة"),
                    "error_code": error_data.get("type", "unknown_error"),
                    "data": error_data
                }
                
        except requests.exceptions.RequestException as e:
            log_entry = PaymentGatewayLog(
                gateway=PaymentGateway.MOYASAR,
                operation="create_invoice",
                request_data=json.dumps(payload) if 'payload' in locals() else "{}",
                response_data=f"Request failed: {str(e)}",
                http_status=0,
                success=False
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return {
                "success": False,
                "error": f"فشل في الاتصال بـ Moyasar: {str(e)}",
                "error_code": "connection_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"خطأ غير متوقع: {str(e)}",
                "error_code": "unexpected_error"
            }
    
    def get_invoice_status(self, invoice_id: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": f"Basic {base64.b64encode(f'{self.api_key}:'.encode()).decode()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/invoices/{invoice_id}",
                headers=headers,
                timeout=self.timeout
            )
            
            log_entry = PaymentGatewayLog(
                gateway=PaymentGateway.MOYASAR,
                operation="get_invoice_status",
                request_data=json.dumps({"invoice_id": invoice_id}),
                response_data=response.text,
                http_status=response.status_code,
                success=response.status_code == 200
            )
            self.db.add(log_entry)
            self.db.commit()
            
            if response.status_code == 200:
                invoice_data = response.json()
                return {
                    "success": True,
                    "status": invoice_data["status"],
                    "amount": invoice_data["amount"],
                    "currency": invoice_data["currency"],
                    "paid_at": invoice_data.get("paid_at"),
                    "data": invoice_data
                }
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("message", "فشل في الاستعلام عن الفاتورة"),
                    "error_code": error_data.get("type", "unknown_error"),
                    "data": error_data
                }
                
        except requests.exceptions.RequestException as e:
            log_entry = PaymentGatewayLog(
                gateway=PaymentGateway.MOYASAR,
                operation="get_invoice_status",
                request_data=json.dumps({"invoice_id": invoice_id}),
                response_data=f"Request failed: {str(e)}",
                http_status=0,
                success=False
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return {
                "success": False,
                "error": f"فشل في الاتصال بـ Moyasar: {str(e)}",
                "error_code": "connection_error"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"خطأ غير متوقع: {str(e)}",
                "error_code": "unexpected_error"
            }
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        try:
            if not self.webhook_secret:
                return {
                    "success": False,
                    "error": "Webhook secret not configured",
                    "error_code": "configuration_error"
                }
            
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return {
                    "success": False,
                    "error": "Invalid webhook signature",
                    "error_code": "invalid_signature"
                }
            
            webhook_data = json.loads(payload.decode())
            
            log_entry = PaymentGatewayLog(
                gateway=PaymentGateway.MOYASAR,
                operation="process_webhook",
                request_data=payload.decode(),
                response_data=json.dumps(webhook_data),
                http_status=200,
                success=True
            )
            self.db.add(log_entry)
            
            event_type = webhook_data.get("type")
            
            if event_type == "invoice_paid":
                result = self._handle_invoice_paid(webhook_data)
            elif event_type == "invoice_failed":
                result = self._handle_invoice_failed(webhook_data)
            else:
                result = {
                    "success": True,
                    "message": f"Webhook event '{event_type}' received but not processed",
                    "event_type": event_type
                }
            
            self.db.commit()
            return result
            
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON payload",
                "error_code": "invalid_json"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"خطأ في معالجة الـ webhook: {str(e)}",
                "error_code": "processing_error"
            }
    
    def _handle_invoice_paid(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            invoice_data = webhook_data.get("data", {})
            invoice_id = invoice_data.get("id")
            
            if not invoice_id:
                return {
                    "success": False,
                    "error": "Invoice ID missing from webhook data",
                    "error_code": "missing_invoice_id"
                }
            
            payment = self.db.query(Payment).filter(
                Payment.transaction_id == invoice_id
            ).first()
            
            if not payment:
                return {
                    "success": False,
                    "error": f"Payment not found for invoice {invoice_id}",
                    "error_code": "payment_not_found"
                }
            
            payment.payment_status = PaymentStatus.PAID
            payment.confirmed_at = datetime.utcnow()
            payment.gateway_response = json.dumps(webhook_data)
            
            if payment.invoice:
                payment.invoice.status = PaymentStatus.PAID
                payment.invoice.paid_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Payment confirmed successfully",
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": f"خطأ في معالجة دفع ناجح: {str(e)}",
                "error_code": "processing_error"
            }
    
    def _handle_invoice_failed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            invoice_data = webhook_data.get("data", {})
            invoice_id = invoice_data.get("id")
            
            if not invoice_id:
                return {
                    "success": False,
                    "error": "Invoice ID missing from webhook data",
                    "error_code": "missing_invoice_id"
                }
            
            payment = self.db.query(Payment).filter(
                Payment.transaction_id == invoice_id
            ).first()
            
            if not payment:
                return {
                    "success": False,
                    "error": f"Payment not found for invoice {invoice_id}",
                    "error_code": "payment_not_found"
                }
            
            payment.payment_status = PaymentStatus.FAILED
            payment.gateway_response = json.dumps(webhook_data)
            
            if payment.invoice:
                payment.invoice.status = PaymentStatus.FAILED
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Payment failure processed successfully",
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": f"خطأ في معالجة فشل الدفع: {str(e)}",
                "error_code": "processing_error"
            }
    
    def get_payment_methods(self) -> Dict[str, Any]:
        return {
            "methods": [
                {
                    "id": "creditcard",
                    "name": "بطاقة ائتمان",
                    "type": "creditcard",
                    "logo": "https://cdn.moyasar.com/assets/creditcard.svg",
                    "supported_brands": ["visa", "mastercard", "mada"]
                },
                {
                    "id": "applepay",
                    "name": "Apple Pay",
                    "type": "applepay",
                    "logo": "https://cdn.moyasar.com/assets/applepay.svg",
                    "supported_devices": ["iphone", "ipad", "mac"]
                },
                {
                    "id": "stcpay",
                    "name": "STC Pay",
                    "type": "stcpay",
                    "logo": "https://cdn.moyasar.com/assets/stcpay.svg",
                    "supported_countries": ["SA"]
                }
            ],
            "currency": "SAR",
            "supported_currencies": ["SAR"]
        } 