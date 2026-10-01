from .closed_box import ClosedBoxAdapter


def get_adapter(generator_id: str):
    if generator_id != 'ClosedBox':
        raise ValueError('此生成器目前仅支持传统二维模式')
    return ClosedBoxAdapter()


def capabilities() -> list[dict]:
    return [{'generatorId':'ClosedBox','adapterVersion':'1.0.0','capabilities':{
        'legacy2d':True,'structuredPanels':True,'manufacturingChecks':False,
        'assembly3d':False,'jointIntervals':False,'faceFeatures':[], 'enhancedExportFormats':[]}}]
