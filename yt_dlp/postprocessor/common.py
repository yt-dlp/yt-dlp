import { readdirSync } from 'fs';
import { join } from 'path';

const postprocessorsDir = join(__dirname, 'postprocessors');

function dynamicImport(modulePath) {
    return import(modulePath);
}

async function genPostprocessorClasses() {
    const postprocessorFiles = readdirSync(postprocessorsDir).filter(file => file.endsWith('.js'));
    const postprocessors = await Promise.all(postprocessorFiles.map(file => dynamicImport(join(postprocessorsDir, file))));
    return postprocessors.map(postprocessor => postprocessor.default);
}

async function genPostprocessors() {
    const postprocessorClasses = await genPostprocessorClasses();
    return postprocessorClasses.map(PostprocessorClass => new PostprocessorClass());
}

async function listPostprocessorClasses(ageLimit = null) {
    const postprocessors = await genPostprocessorClasses();
    return postprocessors.filter(postprocessor => postprocessor.isSuitable(ageLimit)).sort((a, b) => a.name.localeCompare(b.name));
}

async function listPostprocessors(ageLimit = null) {
    const postprocessorClasses = await listPostprocessorClasses(ageLimit);
    return postprocessorClasses.map(PostprocessorClass => new PostprocessorClass());
}

async function getPostprocessor(ppName) {
    const postprocessors = await genPostprocessorClasses();
    return postprocessors.find(postprocessor => postprocessor.name === ppName);
}

export {
    genPostprocessorClasses,
    genPostprocessors,
    listPostprocessorClasses,
    listPostprocessors,
    getPostprocessor
};
