"""NDTT Service - Fetch NDTT reports from external API"""
import os
import requests
import unicodedata
from typing import Optional, Dict
from fastapi import HTTPException, status
from app.data_sources.diccionario_municipios import MUNICIPIOS_COLOMBIA


# NDTT API Configuration
NDTT_LOGIN_URL = "https://ndtt.mincit.gov.co/api/login"
NDTT_INFO_URL = "https://ndtt.mincit.gov.co/api/info-municipio"
NDTT_EMAIL = os.getenv("NDTT_EMAIL", "turismo40@gmail.com")
NDTT_PASSWORD = os.getenv("NDTT_PASSWORD", "Abcd$1234")


def normalize_text(text: str) -> str:
    """Normalizar texto removiendo tildes y convirtiendo a mayúsculas"""
    # Remover tildes
    nfkd = unicodedata.normalize('NFKD', text)
    text_sin_tildes = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return text_sin_tildes.upper().strip()


class NDTTService:
    """Service to interact with NDTT API"""
    
    @staticmethod
    def _get_auth_token() -> Optional[str]:
        """Get authentication token from NDTT API"""
        try:
            response = requests.post(
                NDTT_LOGIN_URL,
                json={"email": NDTT_EMAIL, "password": NDTT_PASSWORD},
                timeout=20
            )
            
            if response.status_code != 200:
                print(f"❌ NDTT Login failed with status {response.status_code}")
                return None
            
            data = response.json()
            token = data.get("token") or data.get("access_token")
            
            if not token:
                print("❌ No token received from NDTT API")
                return None
            
            return token
            
        except Exception as e:
            print(f"❌ Error getting NDTT token: {e}")
            return None
    
    @staticmethod
    def get_municipio_info(nombre_municipio: str) -> Optional[Dict]:
        """
        Get municipality information from NDTT API by name
        
        Args:
            nombre_municipio: Municipality name (e.g., "Aguadas", "Bogotá")
            
        Returns:
            Dictionary with municipality data including url_pdfinforme
        """
        # Normalizar el nombre del municipio
        nombre_normalizado = normalize_text(nombre_municipio)
        
        # Buscar el código del municipio en el diccionario
        cod_municipio = MUNICIPIOS_COLOMBIA.get(nombre_normalizado)
        
        if not cod_municipio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró el código DANE para el municipio '{nombre_municipio}'"
            )
        
        # Obtener token de autenticación
        token = NDTTService._get_auth_token()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo obtener autenticación del servicio NDTT"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            params = {"codmun": cod_municipio}
            
            response = requests.get(
                NDTT_INFO_URL,
                headers=headers,
                params=params,
                timeout=60
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No se encontraron datos NDTT para el municipio '{nombre_municipio}' (código {cod_municipio})"
                    )
                elif response.status_code == 429:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Demasiadas solicitudes al servicio NDTT. Intente más tarde."
                    )
                else:
                    print(f"⚠️ NDTT API returned status {response.status_code}: {response.text[:150]}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Error al consultar el servicio NDTT"
                    )
            
            data = response.json()
            
            # La API devuelve los datos en un array dentro de 'data'
            municipios = data.get('data', [])
            
            if not municipios or len(municipios) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No se encontraron datos NDTT para el municipio '{nombre_municipio}'"
                )
            
            # Obtener el primer municipio del array (debería ser el único con ese código)
            municipio_data = municipios[0]
                
            return {
                "cod_municipio": municipio_data.get("cod_municipio") or cod_municipio,
                "nombre_municipio": municipio_data.get("nombre_municipio") or nombre_municipio,
                "url_pdfinforme": municipio_data.get("url_pdfinforme")
            }
                
        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timeout al consultar el servicio NDTT"
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error fetching NDTT data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al consultar el servicio NDTT"
            )
