import { readdirSync } from 'fs';
import { join } from 'path';

const extractorsDir = join(__dirname, 'extractors');

function dynamicImport(modulePath) {
    return import(modulePath);
}

async function genExtractorClasses() {
    const extractorFiles = readdirSync(extractorsDir).filter(file => file.endsWith('.js'));
    const extractors = await Promise.all(extractorFiles.map(file => dynamicImport(join(extractorsDir, file))));
    return extractors.map(extractor => extractor.default);
}

async function genExtractors() {
    const extractorClasses = await genExtractorClasses();
    return extractorClasses.map(ExtractorClass => new ExtractorClass());
}

async function listExtractorClasses(ageLimit = null) {
    const extractors = await genExtractorClasses();
    return extractors.filter(extractor => extractor.isSuitable(ageLimit)).sort((a, b) => a.name.localeCompare(b.name));
}

async function listExtractors(ageLimit = null) {
    const extractorClasses = await listExtractorClasses(ageLimit);
    return extractorClasses.map(ExtractorClass => new ExtractorClass());
}

async function getInfoExtractor(ieName) {
    const extractors = await genExtractorClasses();
    return extractors.find(extractor => extractor.name === ieName);
}

export {
    genExtractorClasses,
    genExtractors,
    listExtractorClasses,
    listExtractors,
    getInfoExtractor
};
