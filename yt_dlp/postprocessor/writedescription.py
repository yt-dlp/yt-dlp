# yt_dlp/postprocessor/writedescription.py

import os

from .common import PostProcessor

class WriteDescriptionPP(PostProcessor):
    def __init__(self, downloader, **kwargs):
        # O nome do PP que será usado na linha de comando é 'writedescription'
        super().__init__(downloader)

    # O método run é o que executa a lógica do nosso PP
    def run(self, info):
        """Escreve a descrição em um arquivo .description"""
        
        # Pega o nome do arquivo de vídeo que já foi processado
        filepath = info.get('filepath')
        if not filepath:
            self.to_screen('ERROR: Não foi possível encontrar o caminho do arquivo de vídeo.')
            return [], info

        # Pega a descrição do dicionário de informações
        description = info.get('description')
        if not description:
            self.to_screen('Vídeo não tem descrição, pulando a criação do arquivo.')
            return [], info

        # Monta o nome do novo arquivo de descrição
        desc_filename = os.path.splitext(filepath)[0] + '.description'
        
        self.to_screen(f'Writing description to: {desc_filename}')

        try:
            # Escreve o arquivo
            with open(desc_filename, 'w', encoding='utf-8') as f:
                f.write(description)
        except (IOError, OSError) as err:
            self.report_error(f'Cannot write description file: {err}')
            return [], info

        # Retorna a lista de arquivos e o dicionário, como esperado pelo yt-dlp
        return [], info