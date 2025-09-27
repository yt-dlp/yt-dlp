# tests/test_gerador_senha.py
import pytest
import re
from gerador_senha import gerar_senha

# Ciclo 1 do projeto original: Garante que o erro é lançado se nenhuma opção for selecionada.
def test_ciclo1_excecao_sem_criterios():
    with pytest.raises(ValueError):
        gerar_senha(5, minusculas=False, maiusculas=False, digitos=False, simbolos=False)

# Ciclo 2: Nosso alvo para o RED/GREEN de agora.
def test_ciclo2_minusculas_apenas():
    senha = gerar_senha(5, minusculas=True, maiusculas=False, digitos=False, simbolos=False)
    assert len(senha) == 5
    assert re.fullmatch(r'[a-z]{5}', senha)

# Ciclo 3: Teste para minúsculas e maiúsculas.
def test_ciclo3_uma_maiuscula():
    senha = gerar_senha(10, minusculas=True, maiusculas=True, digitos=False, simbolos=False)
    assert len(senha) == 10
    assert any(c.isupper() for c in senha)
    assert any(c.islower() for c in senha)
    assert all(c.isalpha() for c in senha)

# Ciclo 4: Teste para minúsculas e dígitos.
def test_ciclo4_um_digito():
    senha = gerar_senha(12, minusculas=True, maiusculas=False, digitos=True, simbolos=False)
    assert len(senha) == 12
    assert any(c.isdigit() for c in senha)
    assert all(c.islower() or c.isdigit() for c in senha)

# Ciclo 5: Teste para apenas símbolos.
def test_ciclo5_um_simbolo():
    senha = gerar_senha(6, minusculas=False, maiusculas=False, digitos=False, simbolos=True)
    assert len(senha) == 6
    assert any(c in "!@#$%&*" for c in senha)
    assert all(c in "!@#$%&*" for c in senha)

# Ciclo 6: Teste para todas as categorias.
def test_ciclo6_uma_de_cada_categoria():
    senha = gerar_senha(16, minusculas=True, maiusculas=True, digitos=True, simbolos=True)
    assert len(senha) == 16
    assert any(c.islower() for c in senha)
    assert any(c.isupper() for c in senha)
    assert any(c.isdigit() for c in senha)
    assert any(c in "!@#$%&*" for c in senha)

# Ciclo 7: Teste para minúsculas e símbolos.
def test_ciclo7_minusculas_simbolos():
    senha = gerar_senha(10, minusculas=True, maiusculas=False, digitos=False, simbolos=True)
    assert len(senha) == 10
    assert any(c.islower() for c in senha)
    assert any(c in "!@#$%&*" for c in senha)
    assert all(c.islower() or c in "!@#$%&*" for c in senha)